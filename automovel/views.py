
# automovel/views.py


import io
import json
from django.conf import settings
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
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
import openpyxl
from .models import Carro, Carro_agendamento, Carro_checklist, Carro_rastreamento, Carro_manutencao
from .forms import CarroForm, AgendamentoForm, ChecklistForm, ManutencaoForm
from core.mixins import ViewFilialScopedMixin
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from openpyxl.cell import MergedCell
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# --- Mixins ---
class SuccessMessageMixin:
    """ Adiciona uma mensagem de sucesso ao validar um formulário. """
    success_message = ""
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response

# Novo mixin para evitar repetição de código no formulário do Checklist
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
    model = Carro_agendamento

    def get_queryset(self):
        qs = Carro_agendamento.objects.for_request(self.request)
        return qs.select_related('carro', 'usuario').order_by('-data_hora_agenda')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.now().date()
        
        carros_da_filial = Carro.objects.for_request(self.request).filter(ativo=True)
        agendamentos_da_filial = Carro_agendamento.objects.for_request(self.request)
        
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
        eventos = []

        # =======================================================
        # 1. BUSCAR AGENDAMENTOS (Uso do veículo)
        # =======================================================
        agendamentos = Carro_agendamento.objects.for_request(request).filter(cancelar_agenda=False)
        
        status_colors = {
            'agendado': '#0d6efd',      # Azul
            'em_andamento': '#ffc107',  # Amarelo
            'finalizado': '#198754',    # Verde
            'atrasado': '#dc3545'       # Vermelho
        }

        for ag in agendamentos:
            # Proteção caso a data de devolução seja nula (ainda não devolveu)
            # Define duração padrão de 1 hora para visualização se não tiver fim
            start_date = ag.data_hora_agenda
            end_date = ag.data_hora_devolucao if ag.data_hora_devolucao else start_date + timedelta(hours=1)
            
            eventos.append({
                'id': f"ag_{ag.id}", # Prefixo para não confundir com ID de manutenção
                'title': f"{ag.carro.placa} - {ag.funcionario or 'Sem Motorista'}",
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'url': reverse('automovel:agendamento_detail', kwargs={'pk': ag.id}),
                'color': status_colors.get(ag.status, '#6c757d'),
                'extendedProps': {
                    'tipo': 'agendamento',
                    'status': ag.get_status_display()
                }
            })

        # =======================================================
        # 2. BUSCAR MANUTENÇÕES (Revisões, Pneus, etc)
        # =======================================================
        # Filtramos apenas as que não foram concluídas ou todas? 
        # Aqui estou pegando todas para histórico, mas você pode filtrar com .filter(concluida=False)
        manutencoes = Carro_manutencao.objects.for_request(request)

        for man in manutencoes:
            # Define cor baseada na conclusão (Rosa para pendente, Cinza para concluída)
            color_manutencao = '#6c757d' if man.concluida else '#d63384' # #d63384 é um Roxo/Rosa forte
            
            titulo_evento = f"🔧 {man.get_tipo_display()} - {man.carro.placa}"
            if man.concluida:
                titulo_evento = f"✅ (OK) {titulo_evento}"

            eventos.append({
                'id': f"man_{man.id}", # Prefixo diferente
                'title': titulo_evento,
                # Como data_manutencao é DateField (não tem hora), usamos isoformat data pura
                'start': man.data_manutencao.isoformat(), 
                'allDay': True, # Importante: Avisa o calendário que ocupa o dia todo
                'color': color_manutencao,
                # Se você tiver uma view de detalhes da manutenção, use reverse() aqui. 
                # Caso contrário, deixe '#'
                'url': '#', 
                'extendedProps': {
                    'tipo': 'manutencao',
                    'descricao': man.descricao
                }
            })

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
        return super().get_queryset().select_related('filial').prefetch_related('agendamentos', 'manutencoes')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        carro = self.object
        
        # Últimos agendamentos
        agendamentos = carro.agendamentos.all().select_related('usuario').order_by('-data_hora_agenda')[:10]
        
        # Histórico de manutenções
        manutencoes = carro.manutencoes.all().order_by('-data_manutencao')[:10]
        
        context.update({
            'agendamentos': agendamentos,
            'manutencoes': manutencoes,
        })
        return context

    
# --- Agendamento CRUD ---

class AgendamentoListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Carro_agendamento
    template_name = 'automovel/agendamento_list.html'
    context_object_name = 'agendamentos'
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related('carro', 'usuario')

class AgendamentoCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    # MUDANÇA: Removido ViewFilialScopedMixin, pois não se aplica a CreateViews
    model = Carro_agendamento
    form_class = AgendamentoForm
    template_name = 'automovel/agendamento_form.html'
    success_url = reverse_lazy('automovel:agendamento_list')
    success_message = "Agendamento criado com sucesso!"

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.filial = self.request.user.filial_ativa
        return super().form_valid(form)

class AgendamentoUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, UpdateView):
    model = Carro_agendamento
    form_class = AgendamentoForm
    template_name = 'automovel/agendamento_form.html'
    success_message = "Agendamento atualizado com sucesso!"
    def get_success_url(self):
        return reverse('automovel:agendamento_detail', kwargs={'pk': self.object.pk})
    

class AgendamentoDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Carro_agendamento
    template_name = 'automovel/agendamento_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agendamento = self.object
        
        # Histórico de agendamentos para o mesmo carro
        historico_agendamentos = Carro_agendamento.objects.for_request(self.request)\
            .filter(carro=agendamento.carro)\
            .exclude(id=agendamento.id)\
            .select_related('usuario')\
            .order_by('-data_hora_agenda')[:10]
        
        # Dados de rastreamento
        rastreamentos = Carro_rastreamento.objects.filter(agendamento=agendamento)\
            .order_by('-data_hora')[:50]
        
        # Checklist existente
        checklist_saida = agendamento.checklists.filter(tipo='saida').first()
        checklist_retorno = agendamento.checklists.filter(tipo='retorno').first()
        
        context.update({
            'historico_agendamentos': historico_agendamentos,
            'rastreamentos': rastreamentos,
            'checklist_saida': checklist_saida,
            'checklist_retorno': checklist_retorno,
            'mapbox_access_token': settings.MAPBOX_ACCESS_TOKEN if hasattr(settings, 'MAPBOX_ACCESS_TOKEN') else '',
        })
        return context


# --- Checklist CRUD ---

class ChecklistListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Carro_checklist
    template_name = 'automovel/checklist_list.html'
    context_object_name = 'checklists'
    def get_queryset(self):
        # MUDANÇA: Simplificado para confiar apenas no mixin, removendo filtro redundante
        return super().get_queryset().select_related('agendamento__carro')

class ChecklistCreateView(LoginRequiredMixin, SuccessMessageMixin, ChecklistFormSectionsMixin, CreateView):
    model = Carro_checklist
    form_class = ChecklistForm
    template_name = 'automovel/checklist_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.agendamento = get_object_or_404(
            Carro_agendamento.objects.for_request(self.request).select_related('carro'),
            pk=self.kwargs.get('agendamento_pk')
        )
        self.tipo_checklist = self.request.GET.get('tipo', 'saida')

        if Carro_checklist.objects.filter(agendamento=self.agendamento, tipo=self.tipo_checklist).exists():
            messages.error(request, f"Um checklist de '{self.tipo_checklist}' já existe para este agendamento.")
            return redirect('automovel:agendamento_detail', pk=self.agendamento.pk)
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tipo_checklist'] = self.tipo_checklist
        return kwargs

    def get_initial(self):
        return {
            'agendamento': self.agendamento,
            'tipo': self.tipo_checklist,
        }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agendamento'] = self.agendamento
        return context

    def form_valid(self, form):
        agendamento = self.agendamento
        usuario = self.request.user

        # 1. VERIFICAÇÃO DE SEGURANÇA (Primeira coisa a fazer)
        # Se não tiver funcionário, paramos TUDO aqui e retornamos erro.
        if not hasattr(usuario, 'funcionario'):
            messages.error(self.request, "Seu usuário não está vinculado a um cadastro de Funcionário. Contate o RH ou Administrador.")
            return self.form_invalid(form)
        
        # Se passou daqui, é seguro usar usuario.funcionario
        funcionario_logado = usuario.funcionario

        # 2. LÓGICA DE VALIDAÇÃO E ATUALIZAÇÃO DO AGENDAMENTO (KM)
        if self.tipo_checklist == 'saida':
            km_inicial_informado = form.cleaned_data.get('km_inicial')
            if not km_inicial_informado:
                form.add_error('km_inicial', 'A quilometragem inicial é obrigatória para o checklist de saída.')
                return self.form_invalid(form)
            
            agendamento.km_inicial = km_inicial_informado
            agendamento.save(update_fields=['km_inicial'])
        
        elif self.tipo_checklist == 'retorno':
            km_final_informado = form.cleaned_data.get('km_final')
            if not km_final_informado:
                form.add_error('km_final', 'A quilometragem final é obrigatória para o checklist de retorno.')
                return self.form_invalid(form)
            
            agendamento.km_final = km_final_informado
            agendamento.save(update_fields=['km_final'])

        # 3. PREENCHIMENTO AUTOMÁTICO DOS CAMPOS DO CHECKLIST
        form.instance.agendamento = agendamento
        form.instance.usuario = usuario # (Opcional, se o model tiver esse campo)
        
        # Aqui usamos a variável segura que definimos no passo 1
        form.instance.responsavel = funcionario_logado 
        form.instance.filial = funcionario_logado.filial
        
        # 4. DEFINIÇÃO DA MENSAGEM DE SUCESSO
        self.success_message = f"Checklist de {self.tipo_checklist} registrado com sucesso!"
        if self.tipo_checklist == 'retorno':
            self.success_message += " Agendamento finalizado!"

        # Finalmente salva o checklist
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('automovel:agendamento_detail', kwargs={'pk': self.object.agendamento.pk})
    
class ChecklistUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, ChecklistFormSectionsMixin, UpdateView):
    # MUDANÇA: Adicionado ViewFilialScopedMixin (falha de segurança) e SuccessMessageMixin
    model = Carro_checklist
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
    model = Carro_checklist
    template_name = 'automovel/checklist_detail.html'

    context_object_name = 'checklist'
    


# --- Relatórios e APIs ---

# =============================================================================
# CLASSE BASE PARA GERADORES DE RELATÓRIO WORD
# =============================================================================
class BaseWordReportGenerator:
    """
    Classe base para criar relatórios .docx a partir de um único objeto.
    """
    def __init__(self, request, obj, filename_prefix):
        self.request = request
        self.obj = obj
        self.filename = f"{filename_prefix}_{obj.pk}_{datetime.now().strftime('%Y%m%d')}.docx"
        self.document = Document()
        self._setup_styles()

    def _setup_styles(self):
        # Configura estilos que podem ser usados no documento
        # (pode ser expandido com mais estilos)
        pass

    def build_document(self):
        """ As subclasses devem implementar este método para construir o conteúdo do documento. """
        raise NotImplementedError("Subclasses devem implementar 'build_document'")
    
    def add_title(self, text):
        title = self.document.add_heading(text, level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def add_section_heading(self, text):
        self.document.add_heading(text, level=2)

    def generate(self):
        if not self.obj:
            raise Http404("Objeto não encontrado para gerar o relatório.")
            
        self.build_document()
        
        # Prepara a resposta HTTP para o download do arquivo
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{self.filename}"'
        self.document.save(response)
        
        return response

# =============================================================================
# GERADOR ESPECÍFICO PARA O RELATÓRIO DE CHECKLIST
# =============================================================================
class ChecklistWordReportGenerator(BaseWordReportGenerator):
    def __init__(self, request, checklist):
        super().__init__(request, checklist, "vistoria_veicular")

    def _add_summary_table(self):
        checklist = self.obj
        agendamento = checklist.agendamento
        
        table = self.document.add_table(rows=3, cols=4)
        table.style = 'Table Grid'
        
        # Headers
        headers1 = ['Veículo:', 'Data/Hora:', 'KM Inicial:', 'KM Final:']
        headers2 = ['Funcionário:', 'Tipo:']
        
        # Populando a tabela de resumo
        cell_data = {
            (0, 0): f"{agendamento.carro.marca} {agendamento.carro.modelo} - {agendamento.carro.placa}",
            (0, 1): checklist.data_hora.strftime('%d/%m/%Y %H:%M'),
            (0, 2): f"{agendamento.km_inicial or 'N/A'} km",
            (0, 3): f"{agendamento.km_final or 'N/A'} km",
            (1, 0): agendamento.funcionario if agendamento.funcionario else 'N/A',
            (1, 1): checklist.get_tipo_display(),
        }

        # Preenche a tabela
        row1 = table.rows[0].cells
        for i, header in enumerate(headers1):
            row1[i].text = f"{header}\n{cell_data.get((0, i), '')}"
        
        row2 = table.rows[1].cells
        row2[0].text = f"{headers2[0]}\n{cell_data.get((1, 0), '')}"
        row2[1].text = f"{headers2[1]}\n{cell_data.get((1, 1), '')}"

        # Mescla células para melhor layout
        row2[0].merge(row2[1])
        row2[2].merge(row2[3])
        table.rows[2].cells[0].merge(table.rows[2].cells[3]) # Espaço em branco

        for row in table.rows:
            for cell in row.cells:
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    def _add_items_table(self):
        checklist = self.obj
        itens = [
            ("Parte Frontal", checklist.get_revisao_frontal_status_display()),
            ("Parte Traseira", checklist.get_revisao_trazeira_status_display()),
            ("Lado do Motorista", checklist.get_revisao_lado_motorista_status_display()),
            ("Lado do Passageiro", checklist.get_revisao_lado_passageiro_status_display()),
        ]
        
        table = self.document.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Item Vistoriado'
        hdr_cells[1].text = 'Status'

        for item, status in itens:
            row_cells = table.add_row().cells
            row_cells[0].text = item
            row_cells[1].text = status

    def _add_photos(self):
        checklist = self.obj
        photos = [
            ("Evidência Frontal", checklist.foto_frontal),
            ("Evidência Traseira", checklist.foto_trazeira),
            ("Evidência Lado do Motorista", checklist.foto_lado_motorista),
            ("Evidência Lado do Passageiro", checklist.foto_lado_passageiro),
        ]
        
        for title, image_field in photos:
            if image_field:
                self.document.add_paragraph(title, style='Heading 3')
                try:
                    # Adiciona a imagem, com largura controlada
                    self.document.add_picture(image_field.path, width=Inches(4.0))
                except FileNotFoundError:
                    self.document.add_paragraph(f"(Imagem não encontrada em {image_field.path})")
    
    def build_document(self):
        self.add_title("Resumo da Vistoria do Veículo")
        self._add_summary_table()
        
        self.add_section_heading("Itens Vistoriados")
        self._add_items_table()

        self.add_section_heading("Observações Gerais")
        self.document.add_paragraph(self.obj.observacoes_gerais or "Nenhuma observação.")

        self.add_section_heading("Evidências Fotográficas")
        self._add_photos()

# =============================================================================
# VIEW PRINCIPAL PARA RELATÓRIOS WORD
# =============================================================================
def gerar_relatorio_word(request, tipo, pk):
    """
    View que seleciona o gerador de relatório Word correto e o executa.
    """
    generators = {
        'checklist': ChecklistWordReportGenerator,
        # 'agendamento': AgendamentoWordReportGenerator, # Descomente quando criar o de agendamento
    }
    
    models = {
        'checklist': Carro_checklist,
        # 'agendamento': Agendamento,
    }

    generator_class = generators.get(tipo)
    model_class = models.get(tipo)
    
    if not generator_class or not model_class:
        return HttpResponseBadRequest("Tipo de relatório inválido.")

    try:
        # Busca o objeto específico (Checklist ou Agendamento) pelo seu ID (pk)
        obj = model_class.objects.get(pk=pk)
    except model_class.DoesNotExist:
        raise Http404(f"{model_class._meta.verbose_name} não encontrado.")

    generator = generator_class(request, obj)
    return generator.generate()

# =============================================================================
# CLASSE BASE PARA GERADORES DE RELATÓRIO EXCEL
# =============================================================================
class BaseExcelReportGenerator:
    """
    Classe base abstrata para criar relatórios Excel.
    Lida com a criação do Workbook, estilos e resposta HTTP.
    """
    def __init__(self, request, queryset, filename_prefix):
        self.request = request
        self.queryset = queryset
        self.filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        self.header_font = Font(bold=True, color="FFFFFF")
        self.header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        self.header_alignment = Alignment(horizontal="center", vertical="center")
        self.title_font = Font(bold=True, size=16)
        self.title_alignment = Alignment(horizontal="center", vertical="center")
        self.thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    def get_headers(self):
        raise NotImplementedError("Subclasses devem implementar 'get_headers'")

    def get_row_data(self, obj):
        raise NotImplementedError("Subclasses devem implementar 'get_row_data'")

    def get_report_title(self):
        raise NotImplementedError("Subclasses devem implementar 'get_report_title'")

    def _write_headers(self, ws):
        headers = self.get_headers()
        ws.append(headers)
        for cell in ws[2]: # A segunda linha agora contém os cabeçalhos
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = self.header_alignment
            cell.border = self.thin_border

    # --- MÉTODO CORRIGIDO ---
    def _adjust_column_widths(self, ws):
        # Itera sobre todas as colunas da planilha
        for column_cells in ws.columns:
            max_length = 0
            # Pega a letra da coluna a partir da célula do cabeçalho (linha 2),
            # que garantidamente não está mesclada.
            column_letter = column_cells[1].column_letter
            
            for cell in column_cells:
                # Ignora as células mescladas na medição
                if isinstance(cell, MergedCell):
                    continue
                try:
                    if cell.value:
                        # Encontra o comprimento máximo do texto na coluna
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                except:
                    pass
            
            # Adiciona um pouco de espaço extra (padding) e define a largura
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column_letter].width = adjusted_width

    def _write_title(self, ws):
        title = self.get_report_title()
        last_col_letter = get_column_letter(len(self.get_headers()))
        ws.merge_cells(f'A1:{last_col_letter}1')
        cell = ws['A1']
        cell.value = title
        cell.font = self.title_font
        cell.alignment = self.title_alignment

    def generate(self):
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{self.filename}"'
        
        wb = Workbook()
        ws = wb.active
        ws.title = self.get_report_title()[:30]

        self._write_title(ws)
        self._write_headers(ws)
        
        for obj in self.queryset:
            row = self.get_row_data(obj)
            ws.append(row)
            
        self._adjust_column_widths(ws)
        
        wb.save(response)
        return response

# =============================================================================
# GERADORES ESPECÍFICOS PARA CADA TIPO DE RELATÓRIO
# =============================================================================
class CarroReportGenerator(BaseExcelReportGenerator):
    def __init__(self, request, queryset):
        super().__init__(request, queryset, "relatorio_carros")

    @classmethod
    def get_queryset(cls, request):
        return Carro.objects.for_request(request).filter(ativo=True).order_by('marca', 'modelo')

    def get_report_title(self):
        return "Relatório de Carros Ativos"

    def get_headers(self):
        return ['Placa', 'Marca', 'Modelo', 'Ano', 'Cor', 'Disponível', 'Última Manutenção', 'Próxima Manutenção']

    def get_row_data(self, carro):
        return [
            carro.placa,
            carro.marca,
            carro.modelo,
            carro.ano,
            carro.cor,
            "Sim" if carro.disponivel else "Não",
            carro.data_ultima_manutencao.strftime('%d/%m/%Y') if carro.data_ultima_manutencao else 'N/A',
            carro.data_proxima_manutencao.strftime('%d/%m/%Y') if carro.data_proxima_manutencao else 'N/A'
        ]

class AgendamentoReportGenerator(BaseExcelReportGenerator):
    def __init__(self, request, queryset):
        super().__init__(request, queryset, "relatorio_agendamentos")

    @classmethod
    def get_queryset(cls, request):
        return Carro_agendamento.objects.for_request(request).select_related('carro').order_by('-data_hora_agenda')
    
    def get_report_title(self):
        return "Relatório de Agendamentos"

    def get_headers(self):
        return ['ID', 'Veículo', 'Placa', 'Funcionário', 'Data Agendamento', 'Data Devolução', 'Status', 'KM Inicial', 'KM Final', 'Descrição']

    def get_row_data(self, ag):
        return [
            ag.id,
            f"{ag.carro.marca} {ag.carro.modelo}",
            ag.carro.placa,
            ag.funcionario if ag.funcionario else 'N/A',
            ag.data_hora_agenda.strftime('%d/%m/%Y %H:%M') if ag.data_hora_agenda else 'N/A',
            ag.data_hora_devolucao.strftime('%d/%m/%Y %H:%M') if ag.data_hora_devolucao else 'Pendente',
            ag.get_status_display(),
            ag.km_inicial,
            ag.km_final,
            ag.descricao
        ]

# =============================================================================
# VIEW PRINCIPAL - Agora atua como um "despachante"
# =============================================================================
def gerar_relatorio_excel(request, tipo):
    generators = {
        'carros': CarroReportGenerator,
        'agendamentos': AgendamentoReportGenerator,
        'checklists': ChecklistReportGenerator,  # Novo
        'rastreamento': RastreamentoReportGenerator  # Novo
    }
    
    generator_class = generators.get(tipo)
    
    if not generator_class:
        return HttpResponseBadRequest("Tipo de relatório inválido.")
        
    queryset = generator_class.get_queryset(request)
    generator = generator_class(request, queryset)
    
    return generator.generate()

# Novo gerador para Checklists
class ChecklistReportGenerator(BaseExcelReportGenerator):
    def __init__(self, request, queryset):
        super().__init__(request, queryset, "relatorio_checklists")

    @classmethod
    def get_queryset(cls, request):
        return Carro_checklist.objects.for_request(request)\
            .select_related('agendamento__carro', 'usuario')\
            .order_by('-data_hora')

    def get_report_title(self):
        return "Relatório de Checklists"

    def get_headers(self):
        return [
            'ID', 'Agendamento', 'Veículo', 'Tipo', 'Data/Hora', 'Usuário',
            'Status Frontal', 'Status Traseiro', 'Status Motorista', 'Status Passageiro',
            'Observações'
        ]

    def get_row_data(self, checklist):
        return [
            checklist.id,
            f"#{checklist.agendamento.id}",
            f"{checklist.agendamento.carro.placa}",
            checklist.get_tipo_display(),
            checklist.data_hora.strftime('%d/%m/%Y %H:%M'),
            checklist.usuario.get_full_name(),
            checklist.get_revisao_frontal_status_display(),
            checklist.get_revisao_trazeira_status_display(),
            checklist.get_revisao_lado_motorista_status_display(),
            checklist.get_revisao_lado_passageiro_status_display(),
            checklist.observacoes_gerais or 'Nenhuma'
        ]

# As APIs.
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
    

class AgendarManutencaoView(LoginRequiredMixin, View):
    def post(self, request, pk):
        carro = get_object_or_404(Carro.objects.for_request(request), pk=pk)
        
        form = ManutencaoForm(request.POST)
        if form.is_valid():
            manutencao = form.save(commit=False)
            manutencao.carro = carro
            manutencao.usuario = request.user
            manutencao.filial = request.user.filial_ativa
            manutencao.save()
            
            messages.success(request, 'Manutenção agendada com sucesso!')
            return redirect('automovel:carro_detail', pk=carro.pk)
        else:
            messages.error(request, 'Erro ao agendar manutenção. Verifique os dados.')
            return redirect('automovel:carro_detail', pk=carro.pk)

class CarroDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Carro
    template_name = 'automovel/carro_detail.html'

    def get_queryset(self):
        return super().get_queryset().select_related('filial').prefetch_related('agendamentos', 'manutencoes')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        carro = self.object
        
        # Últimos agendamentos
        agendamentos = carro.agendamentos.all().select_related('usuario').order_by('-data_hora_agenda')[:10]
        
        # Histórico de manutenções
        manutencoes = carro.manutencoes.all().order_by('-data_manutencao')[:10]
        
        context.update({
            'agendamentos': agendamentos,
            'manutencoes': manutencoes,
        })
        return context

# Novo gerador para Rastreamento
class RastreamentoReportGenerator(BaseExcelReportGenerator):
    def __init__(self, request, queryset):
        super().__init__(request, queryset, "relatorio_rastreamento")

    @classmethod
    def get_queryset(cls, request):
        return Carro_rastreamento.objects.for_request(request)\
            .select_related('agendamento__carro')\
            .order_by('-data_hora')

    def get_report_title(self):
        return "Relatório de Rastreamento"

    def get_headers(self):
        return [
            'ID', 'Agendamento', 'Veículo', 'Data/Hora', 'Latitude', 'Longitude',
            'Velocidade (km/h)', 'Endereço Aproximado'
        ]

    def get_row_data(self, rastreamento):
        return [
            rastreamento.id,
            f"#{rastreamento.agendamento.id}",
            rastreamento.agendamento.carro.placa,
            rastreamento.data_hora.strftime('%d/%m/%Y %H:%M'),
            float(rastreamento.latitude),
            float(rastreamento.longitude),
            float(rastreamento.velocidade) if rastreamento.velocidade else 'N/A',
            rastreamento.endereco_aproximado or 'N/A'
        ]

class ManutencaoListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Carro_manutencao
    template_name = 'automovel/manutencao_list.html'
    context_object_name = 'manutencoes'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('carro', 'usuario')
        
        # Filtros
        carro_id = self.request.GET.get('carro')
        if carro_id:
            queryset = queryset.filter(carro_id=carro_id)
            
        status = self.request.GET.get('status')
        if status == 'concluidas':
            queryset = queryset.filter(concluida=True)
        elif status == 'pendentes':
            queryset = queryset.filter(concluida=False)
            
        return queryset.order_by('-data_manutencao')

class RastreamentoCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            agendamento_id = data.get('agendamento_id')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            velocidade = data.get('velocidade')
            
            agendamento = get_object_or_404(
                Carro_agendamento.objects.for_request(request),
                pk=agendamento_id
            )
            
            # Geocoding reverso simplificado (em produção, usar serviço como Mapbox/Google)
            endereco_aproximado = self._reverse_geocode(latitude, longitude)
            
            rastreamento = Carro_rastreamento.objects.create(
                agendamento=agendamento,
                latitude=latitude,
                longitude=longitude,
                velocidade=velocidade,
                endereco_aproximado=endereco_aproximado,
                filial=request.user.filial_ativa
            )
            
            return JsonResponse({
                'status': 'success',
                'id': rastreamento.id,
                'endereco': endereco_aproximado,
                'data_hora': rastreamento.data_hora.strftime('%d/%m/%Y %H:%M')
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    def _reverse_geocode(self, lat, lng):
        # Implementação básica - em produção usar serviço profissional
        try:
            # Exemplo com OpenStreetMap Nominatim (gratuito)
            import requests
            response = requests.get(
                f'https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18'
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('display_name', 'Endereço não identificado')
        except:
            pass
        return 'Endereço não disponível'

class RastreamentoMapView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Carro_agendamento
    template_name = 'automovel/rastreamento_map.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agendamento = self.object
        rastreamentos = Carro_rastreamento.objects.filter(agendamento=agendamento)\
            .order_by('data_hora')
        
        pontos_rastreamento = [
            {
                'lat': float(r.latitude),
                'lng': float(r.longitude),
                'data_hora': r.data_hora.strftime('%d/%m/%Y %H:%M'),
                'velocidade': r.velocidade,
                'endereco': r.endereco_aproximado
            }
            for r in rastreamentos
        ]
        
        context.update({
            'pontos_rastreamento': pontos_rastreamento,
            'mapbox_access_token': settings.MAPBOX_ACCESS_TOKEN if hasattr(settings, 'MAPBOX_ACCESS_TOKEN') else '',
        })
        return context

# Removemos LoginRequiredMixin e adicionamos csrf_exempt
@method_decorator(csrf_exempt, name='dispatch')
class RastreamentoAPIView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            
            # SE FOR RASTREADOR FÍSICO (Geralmente enviam IMEI ou ID do dispositivo, não ID do agendamento)
            # Você precisaria buscar qual agendamento está ativo para aquele carro.
            # Para este exemplo, vamos manter sua lógica de receber o ID do agendamento.
            
            agendamento_id = data.get('agendamento_id')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            velocidade = data.get('velocidade')
            
            # Aqui você pode adicionar uma validação de Token simples por segurança
            # token = request.headers.get('Authorization')
            # if token != 'SEU_TOKEN_SECRETO': return JsonResponse({'error': 'Unauthorized'}, status=401)

            agendamento = get_object_or_404(Carro_agendamento, pk=agendamento_id)
            
            # Geocoding reverso (Mantenha sua função _reverse_geocode aqui)
            endereco_aproximado = self._reverse_geocode(latitude, longitude)
            
            rastreamento = Carro_rastreamento.objects.create(
                agendamento=agendamento,
                latitude=latitude,
                longitude=longitude,
                velocidade=velocidade,
                endereco_aproximado=endereco_aproximado,
                # Rastreador não tem usuário logado, então usamos a filial do agendamento
                filial=agendamento.filial 
            )
            
            return JsonResponse({
                'status': 'success', 
                'id': rastreamento.id
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    def _reverse_geocode(self, lat, lng):
        try:
            import requests
            
            # IDENTIFICAÇÃO CORRETA: NomeDoApp/Versão (seu email de contato)
            # Isso evita ser bloqueado pelo servidor do mapa
            headers = {
                'User-Agent': 'ControleTarefas/1.0 (esg@cetestsp.com.br)'
            }
            
            response = requests.get(
                f'https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18',
                headers=headers,
                timeout=5 # Bom adicionar um timeout para não travar o servidor se a internet estiver lenta
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('display_name', 'Endereço não identificado')
                
        except Exception as e:
            print(f"Erro no Geocoding: {e}") # Útil para debug no terminal
            pass
            
        return 'Endereço não disponível'


# ============================================================================
# VIEW PARA EDITAR MANUTENÇÃO (Modal)
# ============================================================================
class ManutencaoUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, UpdateView):
    model = Carro_manutencao
    form_class = ManutencaoForm
    # Não precisa de template_name pois é submetido via Modal, 
    # mas se der erro de validação, o Django precisaria de um. 
    # Por segurança, pode usar o mesmo form de criação ou uma página genérica.
    template_name = 'automovel/manutencao_form.html' 

    def get_success_url(self):
        messages.success(self.request, "Manutenção atualizada com sucesso!")
        # Redireciona de volta para a tela do carro
        return reverse('automovel:carro_detail', kwargs={'pk': self.object.carro.pk})

# ============================================================================
# VIEW PARA FINALIZAR AGENDAMENTO (Modal)
# ============================================================================
class AgendamentoFinalizarView(LoginRequiredMixin, ViewFilialScopedMixin, View):
    def post(self, request, pk):
        # Busca o agendamento (respeitando a filial do usuário via Mixin ou Query)
        agendamento = get_object_or_404(Carro_agendamento, pk=pk)
        
        # Pega os dados do formulário do modal
        km_final = request.POST.get('km_final')
        observacoes = request.POST.get('observacoes_devolucao')
        
        # Validação Básica
        if not km_final:
            messages.error(request, "A Quilometragem Final é obrigatória.")
            return redirect('automovel:carro_detail', pk=agendamento.carro.pk)
        
        try:
            km_final_float = float(km_final)
        except ValueError:
            messages.error(request, "Valor de KM inválido.")
            return redirect('automovel:carro_detail', pk=agendamento.carro.pk)

        # Validação: KM Final não pode ser menor que o KM atual do carro
        if km_final_float < agendamento.carro.quilometragem:
            messages.error(request, f"Erro: O KM informado ({km_final_float}) é menor que o KM atual do veículo ({agendamento.carro.quilometragem}).")
            return redirect('automovel:carro_detail', pk=agendamento.carro.pk)

        # 1. Atualiza o Agendamento
        agendamento.km_final = km_final_float
        agendamento.observacoes_devolucao = observacoes
        agendamento.status = 'finalizado'
        agendamento.data_hora_devolucao = timezone.now()
        agendamento.save()

        # 2. Atualiza o Carro
        carro = agendamento.carro
        carro.quilometragem = km_final_float # Atualiza KM do carro
        carro.disponivel = True # Libera o carro
        carro.save()

        messages.success(request, "Agendamento finalizado e veículo devolvido com sucesso!")
        return redirect('automovel:carro_detail', pk=carro.pk)