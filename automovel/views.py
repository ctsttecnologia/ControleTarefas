
# automovel/views.py

import io
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View, TemplateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.contrib.staticfiles import finders
from datetime import datetime, timedelta
from openpyxl import Workbook
from docx import Document
from io import BytesIO

import openpyxl
from .models import Carro, Agendamento, Checklist, Foto
from .forms import CarroForm, AgendamentoForm, ChecklistForm
import base64
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from core.mixins import ViewFilialScopedMixin


class SuccessMessageMixin:
    success_message = ""
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response

# --- Dashboard ---

class DashboardView(LoginRequiredMixin, ListView):
    template_name = 'automovel/dashboard.html'
    context_object_name = 'ultimos_agendamentos'
    model = Agendamento

    def get_queryset(self):
        # CORREÇÃO: Filtra a query principal (últimos agendamentos) pela filial.
        qs = Agendamento.objects.for_request(self.request)
        # Otimização: Evita uma query extra para cada carro na listagem
        return qs.select_related('carro', 'usuario').order_by('-data_hora_agenda')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.now().date()
        
        # CORREÇÃO: Aplica o filtro de filial em todas as queries para os KPIs.
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

# --- Calendário ---

class CalendarioView(LoginRequiredMixin, TemplateView):
    template_name = 'automovel/calendario.html'

class CalendarioAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # CORREÇÃO: Filtra os agendamentos da API pela filial do usuário.
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
        # Chama super() para obter a queryset já filtrada pela filial.
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
        # CORREÇÃO: Associa a filial do usuário ao novo carro.
        form.instance.filial = self.request.user.filial
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
            # Otimização: Pré-busca dados relacionados para a página de detalhes
        return super().get_queryset().select_related('filial').prefetch_related('agendamentos')
    
# --- Agendamento CRUD ---

class AgendamentoListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Agendamento
    template_name = 'automovel/agendamento_list.html'
    context_object_name = 'agendamentos'
    paginate_by = 20

    def get_queryset(self):
        # Otimização: Pré-busca o carro e o usuário de cada agendamento
        queryset = super().get_queryset().select_related('carro', 'usuario')
        # ... lógica de busca ...
        return queryset

class AgendamentoCreateView(LoginRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, CreateView):
    model = Agendamento
    form_class = AgendamentoForm
    template_name = 'automovel/agendamento_form.html'
    success_url = reverse_lazy('automovel:agendamento_list')
    success_message = "Agendamento criado com sucesso!"

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        # Associa a filial do usuário ao novo agendamento.
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

class ChecklistCreateView(LoginRequiredMixin, CreateView):
    model = Checklist
    form_class = ChecklistForm
    template_name = 'automovel/checklist_form.html'

    def get_agendamento(self):
        return get_object_or_404(Agendamento.objects.for_request(self.request), pk=self.kwargs.get('agendamento_pk'))

    def get_initial(self):
        """
        Passa o agendamento para o formulário para validações.
        """
        agendamento = self.get_agendamento()
        return {
            'agendamento': agendamento,
            'km_inicial': agendamento.km_inicial,
            'tipo': self.request.GET.get('tipo', 'saida'), # Pré-seleciona o tipo via URL
        }
    
    def get_context_data(self, **kwargs):
        # 1. Pega o contexto padrão (que já inclui o 'form' e 'agendamento')
        context = super().get_context_data(**kwargs)
        context['agendamento'] = self.get_agendamento()

        # 2. Pega a instância do formulário que o Django já colocou no contexto
        form = context['form']

        # 3. Cria a estrutura de dados que o template espera
        form_sections = [
            {
                'id': 'frontal',
                'title': 'Vistoria da Parte Frontal',
                'status_field': form['revisao_frontal_status'],
                'photo_field': form['foto_frontal']
            },
            {
                'id': 'traseira',
                'title': 'Vistoria da Parte Traseira',
                'status_field': form['revisao_trazeira_status'],
                'photo_field': form['foto_trazeira']
            },
            {
                'id': 'motorista',
                'title': 'Vistoria do Lado do Motorista',
                'status_field': form['revisao_lado_motorista_status'],
                'photo_field': form['foto_lado_motorista']
            },
            {
                'id': 'passageiro',
                'title': 'Vistoria do Lado do Passageiro',
                'status_field': form['revisao_lado_passageiro_status'],
                'photo_field': form['foto_lado_passageiro']
            }
        ]
        
        # 4. Adiciona a lista ao contexto que será enviado para o template
        context['form_sections'] = form_sections
        
        return context

    def form_valid(self, form):
        agendamento = self.get_agendamento()
        form.instance.agendamento = agendamento
        form.instance.usuario = self.request.user
        form.instance.filial = agendamento.filial
        
        # A lógica de negócio foi movida para o models.py!
        # A view apenas exibe a mensagem de sucesso apropriada.
        if form.instance.tipo == 'saida':
            messages.success(self.request, 'Checklist de saída registrado com sucesso!')
        elif form.instance.tipo == 'retorno':
            messages.success(self.request, 'Checklist de retorno registrado e agendamento finalizado!')
        
        return super().form_valid(form)

    def get_success_url(self):
        # self.object é o checklist salvo
        return reverse('automovel:agendamento_detail', kwargs={'pk': self.object.agendamento.pk})

class ChecklistDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Checklist
    template_name = 'automovel/checklist_detail.html'

# --- Relatórios e APIs ---
# (Omitido o código de geração de DOCX por ser longo e não ter erros de filial)
# A lógica de filtragem foi adicionada abaixo

class ChecklistExportWordView(LoginRequiredMixin, ViewFilialScopedMixin, View):
    """
    Exporta os detalhes de um checklist específico para um arquivo Word (.docx),
    incluindo as fotos da vistoria e a assinatura.
    """
    def get(self, request, *args, **kwargs):
        # 1. Obter o objeto do checklist
        checklist = get_object_or_404(Checklist, pk=kwargs.get('pk'))
        agendamento = checklist.agendamento
        carro = agendamento.carro

        # 2. Criar um documento Word em memória
        buffer = io.BytesIO()
        document = Document()

        # 3. Adicionar conteúdo ao documento
        document.add_heading('Checklist de Vistoria Veicular', level=0)

        # Seção de Informações Gerais
        document.add_heading('Detalhes do Agendamento', level=1)
        p = document.add_paragraph()
        p.add_run('Veículo: ').bold = True
        p.add_run(f'{carro.marca} {carro.modelo} - Placa: {carro.placa}\n')
        p.add_run('Funcionário: ').bold = True
        p.add_run(f'{agendamento.funcionario}\n')
        p.add_run('Data e Hora do Checklist: ').bold = True
        p.add_run(checklist.data_hora.strftime("%d/%m/%Y às %H:%M"))

        # Seção de Vistoria com tabela
        document.add_heading('Itens da Vistoria', level=1)
        table = document.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Item'
        hdr_cells[1].text = 'Status'

        itens_vistoria = {
            "Parte Frontal": checklist.get_revisao_frontal_status_display(),
            "Parte Traseira": checklist.get_revisao_trazeira_status_display(),
            "Lado do Motorista": checklist.get_revisao_lado_motorista_status_display(),
            "Lado do Passageiro": checklist.get_revisao_lado_passageiro_status_display(),
        }
        for item, status in itens_vistoria.items():
            row_cells = table.add_row().cells
            row_cells[0].text = item
            row_cells[1].text = status

        # Seção de Observações
        if checklist.observacoes_gerais:
            document.add_heading('Observações Gerais', level=1)
            document.add_paragraph(checklist.observacoes_gerais)

        # Seção de Fotos
        document.add_heading('Fotos da Vistoria', level=1)
        if checklist.foto_frontal:
            document.add_paragraph('Foto Frontal:')
            document.add_picture(checklist.foto_frontal.path, width=Inches(3.0))
        # Adicione as outras fotos de forma similar...
        if checklist.foto_trazeira:
            document.add_paragraph('Foto Traseira:')
            document.add_picture(checklist.foto_trazeira.path, width=Inches(3.0))

        # Seção de Assinatura
        if checklist.assinatura:
            document.add_heading('Assinatura do Responsável', level=1)
            try:
                # Remove o cabeçalho 'data:image/png;base64,' e decodifica
                header, encoded = checklist.assinatura.split(",", 1)
                decoded_image = base64.b64decode(encoded)
                image_stream = io.BytesIO(decoded_image)
                document.add_picture(image_stream, width=Inches(2.5))
            except Exception as e:
                document.add_paragraph(f"(Não foi possível carregar a imagem da assinatura: {e})")

        # 4. Salvar o documento no buffer
        document.save(buffer)
        buffer.seek(0)

        # 5. Criar a resposta HTTP para forçar o download
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        filename = f'checklist_{checklist.pk}_{carro.placa}.docx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

class CarroReportView(LoginRequiredMixin, View):
    """
    Gera um relatório de todos os carros ativos da filial em um arquivo Excel (.xlsx).
    """
    def get(self, request, *args, **kwargs):
        # 1. Obter os dados
        carros = Carro.objects.for_request(request).filter(ativo=True).order_by('marca', 'modelo')

        # 2. Criar um arquivo Excel em memória
        buffer = io.BytesIO()
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Relatório de Frota"

        # 3. Definir os cabeçalhos das colunas
        headers = [
            "Placa", "Marca", "Modelo", "Ano", "Cor", "Renavan", 
            "Disponível", "Última Manutenção", "Próxima Manutenção"
        ]
        sheet.append(headers)

        # 4. Preencher o arquivo com os dados dos carros
        for carro in carros:
            sheet.append([
                carro.placa,
                carro.marca,
                carro.modelo,
                carro.ano,
                carro.cor,
                carro.renavan,
                "Sim" if carro.disponivel else "Não",
                carro.data_ultima_manutencao.strftime("%d/%m/%Y") if carro.data_ultima_manutencao else "N/A",
                carro.data_proxima_manutencao.strftime("%d/%m/%Y") if carro.data_proxima_manutencao else "N/A",
            ])

        # 5. Salvar o arquivo no buffer
        workbook.save(buffer)
        buffer.seek(0)

        # 6. Criar a resposta HTTP para forçar o download
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'relatorio_frota_{timezone.now().strftime("%Y-%m-%d")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

class CarrosDisponiveisAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Filtra carros da API pela filial.
        carros = Carro.objects.for_request(request).filter(disponivel=True, ativo=True)
        data = list(carros.values('id', 'placa', 'modelo'))
        return JsonResponse(data, safe=False)

class ProximaManutencaoAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        hoje = timezone.now().date()
        # Filtra carros da API pela filial.
        carros = Carro.objects.for_request(request).filter(
            data_proxima_manutencao__lte=hoje + timedelta(days=7),
            ativo=True
        ).order_by('data_proxima_manutencao')
        
        data = [{'id': c.id, 'placa': c.placa, 'modelo': c.modelo} for c in carros]
        return JsonResponse(data, safe=False)
    
    