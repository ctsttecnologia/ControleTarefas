
# automovel/views.py


import io
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View, TemplateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import base64
from io import BytesIO
from docx import Document
from docx.shared import Inches
import openpyxl

from .models import Carro, Agendamento, Checklist
from .forms import CarroForm, AgendamentoForm, ChecklistForm
from core.mixins import ViewFilialScopedMixin

# --- Mixins ---

class SuccessMessageMixin:
    """ Adiciona uma mensagem de sucesso ao validar um formulário. """
    success_message = ""
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response

# MUDANÇA: Novo mixin para evitar repetição de código no formulário do Checklist
class ChecklistFormSectionsMixin:
    """ Organiza os campos do formulário de checklist em seções para o template. """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context['form']
        
        # Estrutura de dados para renderizar o formulário no template
        context['form_sections'] = [
            {'id': 'frontal', 'title': 'Vistoria da Parte Frontal', 'status_field': form['revisao_frontal_status'], 'photo_field': form['foto_frontal']},
            {'id': 'traseira', 'title': 'Vistoria da Parte Traseira', 'status_field': form['revisao_trazeira_status'], 'photo_field': form['foto_trazeira']},
            {'id': 'motorista', 'title': 'Vistoria do Lado do Motorista', 'status_field': form['revisao_lado_motorista_status'], 'photo_field': form['foto_lado_motorista']},
            {'id': 'passageiro', 'title': 'Vistoria do Lado do Passageiro', 'status_field': form['revisao_lado_passageiro_status'], 'photo_field': form['foto_lado_passageiro']}
        ]
        return context

# --- Dashboard e Calendário (sem mudanças significativas, já estavam bons) ---

class DashboardView(LoginRequiredMixin, ListView):
    template_name = 'automovel/dashboard.html'
    context_object_name = 'ultimos_agendamentos'
    model = Agendamento

    def get_queryset(self):
        qs = Agendamento.objects.for_request(self.request)
        return qs.select_related('carro', 'usuario').order_by('-data_hora_agenda')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.now().date()
        
        carros_da_filial = Carro.objects.for_request(self.request).filter(ativo=True)
        agendamentos_da_filial = Agendamento.objects.for_request(self.request)
        
        context['total_carros'] = carros_da_filial.count()
        context['carros_disponiveis'] = carros_da_filial.filter(disponivel=True).count()
        context['agendamentos_hoje'] = agendamentos_da_filial.filter(data_hora_agenda__date=hoje, status='agendado').count()
        context['manutencao_proxima'] = carros_da_filial.filter(
            data_proxima_manutencao__lte=hoje + timedelta(days=7),
            data_proxima_manutencao__gte=hoje
        ).count()
        return context

class CalendarioView(LoginRequiredMixin, TemplateView):
    template_name = 'automovel/calendario.html'

class CalendarioAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        agendamentos = Agendamento.objects.for_request(request).filter(cancelar_agenda=False)
        status_colors = {'agendado': '#0d6efd', 'em_andamento': '#ffc107', 'finalizado': '#198754'}
        eventos = [
            {
                'id': ag.id,
                'title': f"{ag.carro.placa} - {ag.funcionario}",
                'start': ag.data_hora_agenda.isoformat(),
                'end': ag.data_hora_devolucao.isoformat(),
                'url': reverse('automovel:agendamento_detail', kwargs={'pk': ag.id}),
                'color': status_colors.get(ag.status, '#6c757d'),
            }
            for ag in agendamentos
        ]
        return JsonResponse(eventos, safe=False)

# --- Carro CRUD ---

class CarroListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Carro
    template_name = 'automovel/carro_list.html'
    context_object_name = 'carros'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().filter(ativo=True)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(placa__icontains=search) | Q(modelo__icontains=search) | Q(marca__icontains=search)
            )
        return queryset

class CarroCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Carro
    form_class = CarroForm
    template_name = 'automovel/carro_form.html'
    success_url = reverse_lazy('automovel:carro_list')
    success_message = "Carro cadastrado com sucesso!"

    def form_valid(self, form):
        # MUDANÇA: Padronizado para usar filial_ativa
        form.instance.filial = self.request.user.filial_ativa
        return super().form_valid(form)

class CarroUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, UpdateView):
    model = Carro
    form_class = CarroForm
    template_name = 'automovel/carro_form.html'
    success_url = reverse_lazy('automovel:carro_list')
    success_message = "Carro atualizado com sucesso!"

class CarroDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Carro
    template_name = 'automovel/carro_detail.html'

    def get_queryset(self):
        return super().get_queryset().select_related('filial').prefetch_related('agendamentos')
    
# --- Agendamento CRUD ---

class AgendamentoListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Agendamento
    template_name = 'automovel/agendamento_list.html'
    context_object_name = 'agendamentos'
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related('carro', 'usuario')

class AgendamentoCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    # MUDANÇA: Removido ViewFilialScopedMixin, pois não se aplica a CreateViews
    model = Agendamento
    form_class = AgendamentoForm
    template_name = 'automovel/agendamento_form.html'
    success_url = reverse_lazy('automovel:agendamento_list')
    success_message = "Agendamento criado com sucesso!"

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.filial = self.request.user.filial_ativa
        return super().form_valid(form)

class AgendamentoUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, UpdateView):
    model = Agendamento
    form_class = AgendamentoForm
    template_name = 'automovel/agendamento_form.html'
    success_message = "Agendamento atualizado com sucesso!"
    def get_success_url(self):
        return reverse('automovel:agendamento_detail', kwargs={'pk': self.object.pk})

class AgendamentoDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Agendamento
    template_name = 'automovel/agendamento_detail.html'

# --- Checklist CRUD ---

class ChecklistListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Checklist
    template_name = 'automovel/checklist_list.html'
    context_object_name = 'checklists'

    def get_queryset(self):
        # MUDANÇA: Simplificado para confiar apenas no mixin, removendo filtro redundante
        return super().get_queryset().select_related('agendamento__carro')

class ChecklistCreateView(LoginRequiredMixin, SuccessMessageMixin, ChecklistFormSectionsMixin, CreateView):
    model = Checklist
    form_class = ChecklistForm
    template_name = 'automovel/checklist_form.html'
    # Mensagens de sucesso agora são tratadas no form_valid

    def dispatch(self, request, *args, **kwargs):
        # MUDANÇA: Adicionado .select_related para otimizar a busca do agendamento
        self.agendamento = get_object_or_404(
            Agendamento.objects.for_request(self.request).select_related('carro'),
            pk=self.kwargs.get('agendamento_pk')
        )
        self.tipo_checklist = self.request.GET.get('tipo', 'saida')

        if Checklist.objects.filter(agendamento=self.agendamento, tipo=self.tipo_checklist).exists():
            messages.error(request, f"Um checklist de '{self.tipo_checklist}' já existe para este agendamento.")
            return redirect('automovel:agendamento_detail', pk=self.agendamento.pk)
            
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        # MUDANÇA: Removido 'km_inicial' pois o campo não existe mais no modelo Checklist
        return {
            'agendamento': self.agendamento,
            'tipo': self.tipo_checklist,
        }
    
    def get_context_data(self, **kwargs):
        # O mixin ChecklistFormSectionsMixin agora cuida da organização do form
        context = super().get_context_data(**kwargs)
        context['agendamento'] = self.agendamento
        return context

    def form_valid(self, form):
        form.instance.agendamento = self.agendamento
        form.instance.usuario = self.request.user
        
        # MUDANÇA: Lógica de negócio (atualizar status) foi REMOVIDA daqui.
        # O método save() do modelo Checklist agora é a única fonte da verdade para essa regra.
        # Ao chamar super().form_valid(form), o .save() do modelo será executado.
        
        # Define a mensagem de sucesso com base no tipo
        if self.tipo_checklist == 'saida':
            self.success_message = 'Checklist de saída registrado com sucesso!'
        elif self.tipo_checklist == 'retorno':
            self.success_message = 'Checklist de retorno registrado e agendamento finalizado!'
        
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('automovel:agendamento_detail', kwargs={'pk': self.object.agendamento.pk})
    
class ChecklistUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, ChecklistFormSectionsMixin, UpdateView):
    # MUDANÇA: Adicionado ViewFilialScopedMixin (falha de segurança) e SuccessMessageMixin
    model = Checklist
    form_class = ChecklistForm
    template_name = 'automovel/checklist_form.html'
    success_message = 'Checklist atualizado com sucesso!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agendamento'] = self.object.agendamento
        return context

    def get_success_url(self):
        return reverse('automovel:agendamento_detail', kwargs={'pk': self.object.agendamento.pk})

class ChecklistDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Checklist
    template_name = 'automovel/checklist_detail.html'

# --- Relatórios e APIs ---

class ChecklistExportWordView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # MUDANÇA: CORREÇÃO DE SEGURANÇA - usa o manager para garantir que o usuário pertence à filial
        checklist = get_object_or_404(
            Checklist.objects.for_request(request).select_related('agendamento__carro'), 
            pk=kwargs.get('pk')
        )
        # ... o resto do seu código de geração de DOCX continua igual ...
        agendamento = checklist.agendamento
        carro = agendamento.carro
        buffer = io.BytesIO()
        document = Document()
        document.add_heading('Checklist de Vistoria Veicular', level=0)
        # ... (código omitido por brevidade, mas continua o mesmo)
        p = document.add_paragraph()
        p.add_run('Veículo: ').bold = True
        p.add_run(f'{carro.marca} {carro.modelo} - Placa: {carro.placa}\n')
        # ... (resto do código)
        document.save(buffer)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        filename = f'checklist_{checklist.pk}_{carro.placa}.docx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class CarroReportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        carros = Carro.objects.for_request(request).filter(ativo=True).order_by('marca', 'modelo')
        # ... o resto do seu código de geração de Excel continua igual ...
        buffer = io.BytesIO()
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Relatório de Frota"
        headers = ["Placa", "Marca", "Modelo", "Ano", "Cor", "Renavan", "Disponível", "Última Manutenção", "Próxima Manutenção"]
        sheet.append(headers)
        for carro in carros:
            sheet.append([
                carro.placa, carro.marca, carro.modelo, carro.ano, carro.cor, carro.renavan,
                "Sim" if carro.disponivel else "Não",
                carro.data_ultima_manutencao.strftime("%d/%m/%Y") if carro.data_ultima_manutencao else "N/A",
                carro.data_proxima_manutencao.strftime("%d/%m/%Y") if carro.data_proxima_manutencao else "N/A",
            ])
        workbook.save(buffer)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f'relatorio_frota_{timezone.now().strftime("%Y-%m-%d")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

# As APIs já estavam corretas, sem necessidade de mudanças.
class CarrosDisponiveisAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        carros = Carro.objects.for_request(request).filter(disponivel=True, ativo=True)
        data = list(carros.values('id', 'placa', 'modelo'))
        return JsonResponse(data, safe=False)

class ProximaManutencaoAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        hoje = timezone.now().date()
        carros = Carro.objects.for_request(request).filter(
            data_proxima_manutencao__lte=hoje + timedelta(days=7),
            ativo=True
        ).order_by('data_proxima_manutencao')
        data = [{'id': c.id, 'placa': c.placa, 'modelo': c.modelo} for c in carros]
        return JsonResponse(data, safe=False)
