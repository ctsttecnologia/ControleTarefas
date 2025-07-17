
# automovel/views.py

from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
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

from .models import Carro, Agendamento, Checklist, Foto
from .forms import CarroForm, AgendamentoForm, ChecklistForm, FotoForm

import base64
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH



# --- Mixins reutilizáveis ---
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

    def get_queryset(self):
        return Agendamento.objects.order_by('-data_hora_agenda')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.now().date()
        
        carros_qs = Carro.objects.filter(ativo=True)
        context['total_carros'] = carros_qs.count()
        context['carros_disponiveis'] = carros_qs.filter(disponivel=True).count()
        context['agendamentos_hoje'] = Agendamento.objects.filter(data_hora_agenda__date=hoje, status='agendado').count()
        context['manutencao_proxima'] = carros_qs.filter(data_proxima_manutencao__lte=hoje + timedelta(days=7), data_proxima_manutencao__gte=hoje).count()
        return context

# --- Carro CRUD ---
class CarroListView(LoginRequiredMixin, ListView):
    model = Carro
    template_name = 'automovel/carro_list.html'
    context_object_name = 'carros'
    paginate_by = 10

    def get_queryset(self):
        queryset = Carro.objects.filter(ativo=True)
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

class CarroUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Carro
    form_class = CarroForm
    template_name = 'automovel/carro_form.html'
    success_url = reverse_lazy('automovel:carro_list')
    success_message = "Carro atualizado com sucesso!"

class CarroDetailView(LoginRequiredMixin, DetailView):
    model = Carro
    template_name = 'automovel/carro_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agendamentos'] = self.object.agendamentos.order_by('-data_hora_agenda')[:10]
        return context

# --- Agendamento CRUD ---
class AgendamentoListView(LoginRequiredMixin, ListView):
    model = Agendamento
    template_name = 'automovel/agendamento_list.html'
    context_object_name = 'agendamentos'
    paginate_by = 10

class AgendamentoCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Agendamento
    form_class = AgendamentoForm
    template_name = 'automovel/agendamento_form.html'
    success_url = reverse_lazy('automovel:agendamento_list')
    success_message = "Agendamento criado com sucesso!"

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class AgendamentoUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Agendamento
    form_class = AgendamentoForm
    template_name = 'automovel/agendamento_form.html'
    success_message = "Agendamento atualizado com sucesso!"
    def get_success_url(self):
        return reverse('automovel:agendamento_detail', kwargs={'pk': self.object.pk})

class AgendamentoDetailView(LoginRequiredMixin, DetailView):
    model = Agendamento
    template_name = 'automovel/agendamento_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['checklist_saida'] = self.object.checklists.filter(tipo='saida').first()
        context['checklist_retorno'] = self.object.checklists.filter(tipo='retorno').first()
        context['fotos'] = self.object.fotos.all()
        return context

# --- Checklist CRUD ---
class ChecklistCreateView(LoginRequiredMixin, CreateView):
    model = Checklist
    form_class = ChecklistForm
    template_name = 'automovel/checklist_form.html'

    def get_initial(self):
        initial = super().get_initial()
        agendamento = get_object_or_404(Agendamento, pk=self.kwargs.get('agendamento_pk'))
        
        if agendamento.status == 'em_andamento':
            initial['tipo'] = 'retorno'
            checklist_saida = Checklist.objects.filter(agendamento=agendamento, tipo='saida').first()
            if checklist_saida:
                initial['km_inicial'] = checklist_saida.km_inicial
        else:
            initial['tipo'] = 'saida'
            initial['km_inicial'] = agendamento.km_inicial
            
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agendamento = get_object_or_404(Agendamento, pk=self.kwargs.get('agendamento_pk'))
        context['agendamento'] = agendamento
        
        form = context['form']
        context['form_sections'] = [
            {'title': 'Parte Frontal', 'id': 'frontal', 'status_field': form['revisao_frontal_status'], 'photo_field': form['foto_frontal']},
            {'title': 'Parte Traseira', 'id': 'traseira', 'status_field': form['revisao_trazeira_status'], 'photo_field': form['foto_trazeira']},
            {'title': 'Lado do Motorista', 'id': 'lado_motorista', 'status_field': form['revisao_lado_motorista_status'], 'photo_field': form['foto_lado_motorista']},
            {'title': 'Lado do Passageiro', 'id': 'lado_passageiro', 'status_field': form['revisao_lado_passageiro_status'], 'photo_field': form['foto_lado_passageiro']}
        ]
        return context
    
    # PASSO DE DIAGNÓSTICO: Adicionar este método para ver os erros no console
    def form_invalid(self, form):
        print("ERROS DE VALIDAÇÃO DO FORMULÁRIO:")
        print(form.errors.as_json())
        messages.error(self.request, "O formulário contém erros. Por favor, verifique os campos marcados.")
        return super().form_invalid(form)

    def form_valid(self, form):
        agendamento = get_object_or_404(Agendamento, pk=self.kwargs.get('agendamento_pk'))
        form.instance.agendamento = agendamento
        form.instance.usuario = self.request.user
        
        response = super().form_valid(form)
        checklist = self.object

        if checklist.tipo == 'saida':
            agendamento.status = 'em_andamento'
            messages.success(self.request, 'Checklist de saída registrado com sucesso!')
        elif checklist.tipo == 'retorno':
            agendamento.status = 'finalizado'
            if checklist.km_final:
                agendamento.km_final = checklist.km_final
            messages.success(self.request, 'Checklist de retorno registrado e agendamento finalizado!')
        
        agendamento.save()
        return response

    def get_success_url(self):
        return reverse('automovel:agendamento_detail', kwargs={'pk': self.object.agendamento.pk})


# --- Exportações e Relatórios (Convertidos para CBV) ---
class BaseExportView(LoginRequiredMixin, View):
    model = None
    filename_prefix = 'relatorio'
    
    def get_object(self):
        return get_object_or_404(self.model, pk=self.kwargs.get('pk'))

    def get(self, request, *args, **kwargs):
        raise NotImplementedError("Subclasses devem implementar o método get.")

class ChecklistExportWordView(BaseExportView):
    model = Checklist

    def get(self, request, *args, **kwargs):
        checklist = self.get_object()
        document = Document()

        # --- 1. Adicionar Logomarca ao Cabeçalho (LINHA CORRIGIDA) ---
        # O caminho não deve incluir 'static/'. Ele deve ser relativo
        # à pasta static da sua aplicação ou de STATICFILES_DIRS.
        # Tente um destes, dependendo da sua estrutura de pastas:
        logo_path = finders.find('automovel/images/logocetest.png')
        
        # Se a primeira tentativa não funcionar, sua estrutura pode ser mais simples:
        if not logo_path:
            logo_path = finders.find('images/logocetest.png')

        # Debug: Verifique no console do runserver o que está sendo encontrado
        print(f"Caminho encontrado para a logo: {logo_path}")

        if logo_path:
            header = document.sections[0].header
            # Limpa o parágrafo padrão do cabeçalho, se houver
            if header.paragraphs:
                p = header.paragraphs[0]
                p.clear()
            else:
                p = header.add_paragraph()

            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            run = p.add_run()
            run.add_picture(logo_path, height=Inches(0.6))
        else:
            print("AVISO: Logomarca não encontrada. Verifique o caminho e as configurações de arquivos estáticos.")


        # --- 2. Título do Documento ---
        document.add_heading(f'Relatório de Checklist - {checklist.get_tipo_display()}', level=1)

        # --- 3. Tabela de Informações Gerais ---
        document.add_heading('Dados Gerais', level=2)
        table_info = document.add_table(rows=0, cols=4)
        table_info.style = 'Table Grid'
        
        info_data = {
            "Veículo:": str(checklist.agendamento.carro), "Data/Hora:": checklist.data_hora.strftime("%d/%m/%Y %H:%M"),
            "Funcionário:": checklist.agendamento.funcionario, "KM Inicial:": f"{checklist.km_inicial} km",
            "Responsável:": checklist.agendamento.responsavel, "KM Final:": f"{checklist.km_final or 'N/A'} km",
        }
        keys = list(info_data.keys())
        for i in range(0, len(keys), 2):
            row_cells = table_info.add_row().cells
            row_cells[0].text = keys[i]
            row_cells[0].paragraphs[0].runs[0].font.bold = True
            row_cells[1].text = info_data[keys[i]]
            if i + 1 < len(keys):
                row_cells[2].text = keys[i+1]
                row_cells[2].paragraphs[0].runs[0].font.bold = True
                row_cells[3].text = info_data[keys[i+1]]

        # --- 4. Tabela de Itens de Vistoria ---
        document.add_heading('Itens Vistoriados', level=2)
        table_items = document.add_table(rows=1, cols=2)
        table_items.style = 'Table Grid'
        hdr_cells = table_items.rows[0].cells
        hdr_cells[0].text = 'Item'
        hdr_cells[1].text = 'Status'
        
        items_data = [
            ("Parte Frontal", checklist.get_revisao_frontal_status_display()),
            ("Parte Traseira", checklist.get_revisao_trazeira_status_display()),
            ("Lado do Motorista", checklist.get_revisao_lado_motorista_status_display()),
            ("Lado do Passageiro", checklist.get_revisao_lado_passageiro_status_display()),
        ]
        for item, status in items_data:
            row_cells = table_items.add_row().cells
            row_cells[0].text = item
            row_cells[1].text = status

        # --- 5. Observações e Evidências Fotográficas ---
        if checklist.observacoes_gerais:
            document.add_heading('Observações Gerais', level=2)
            document.add_paragraph(checklist.observacoes_gerais)
        
        document.add_heading('Evidências Fotográficas', level=2)
        for part in ['frontal', 'trazeira', 'lado_motorista', 'lado_passageiro']:
            photo_field = getattr(checklist, f'foto_{part}')
            if photo_field:
                document.add_paragraph(f'Foto da Parte {part.replace("_", " ").title()}:', style='Intense Quote')
                document.add_picture(photo_field.path, width=Inches(5.0))
        
        # --- 6. Assinatura ---
        if checklist.assinatura:
            document.add_heading('Assinatura do Responsável', level=2)
            try:
                # Decodifica a assinatura em Base64 para um buffer de imagem
                img_data = base64.b64decode(checklist.assinatura.split(',')[1])
                img_buffer = BytesIO(img_data)
                document.add_picture(img_buffer, width=Inches(3.0))
            except Exception:
                document.add_paragraph("Não foi possível carregar a imagem da assinatura.")

        # --- 7. Gerar Resposta ---
        buffer = BytesIO()
        document.save(buffer)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename=checklist_{checklist.id}.docx'
        return response

class ChecklistDetailView(LoginRequiredMixin, DetailView):
    model = Checklist
    template_name = 'automovel/checklist_detail.html'
    context_object_name = 'checklist'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Checklist de {self.object.get_tipo_display()} - Agendamento #{self.object.agendamento.id}"
        return context

class CarroReportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        file_format = self.kwargs.get('format')
        carros = Carro.objects.filter(ativo=True)
        
        if file_format == 'excel':
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="relatorio_carros.xlsx"'
            wb = Workbook()
            ws = wb.active
            ws.title = "Carros"
            # ... (lógica de criação do XLSX) ...
            wb.save(response)
            return response
        
        # Implementar Word se necessário
        return HttpResponse("Formato de relatório não suportado.", status=400)


# --- API Endpoints (Convertidos para CBV) ---
class CarrosDisponiveisAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        carros = Carro.objects.filter(disponivel=True, ativo=True)
        data = list(carros.values('id', 'placa', 'modelo'))
        return JsonResponse(data, safe=False)

class ProximaManutencaoAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        hoje = timezone.now().date()
        carros = Carro.objects.filter(
            data_proxima_manutencao__lte=hoje + timedelta(days=7),
            ativo=True
        ).order_by('data_proxima_manutencao')
        
        data = [{
            'id': carro.id, 'placa': carro.placa, 'modelo': carro.modelo,
            'data_proxima_manutencao': carro.data_proxima_manutencao.strftime('%d/%m/%Y'),
            'dias_restantes': (carro.data_proxima_manutencao - hoje).days
        } for carro in carros]
        return JsonResponse(data, safe=False)
