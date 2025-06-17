
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import UpdateView
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods, require_POST

# Para geração de PDF
from django.template.loader import get_template
from xhtml2pdf import pisa

# Para geração de DOCX
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .models import Tarefas, Comentario, HistoricoStatus
from .forms import TarefaForm, ComentarioForm
import logging

# Outras bibliotecas
from datetime import datetime, timedelta
import io
import os



logger = logging.getLogger(__name__)

# Constantes para status e cores
STATUS_MAP = {
    'pendente': {'label': 'Pendente', 'color': '#FFC107'},
    'andamento': {'label': 'Andamento', 'color': '#2196F3'},
    'concluida': {'label': 'Concluída', 'color': '#4CAF50'},
    'cancelada': {'label': 'Cancelada', 'color': '#F44336'},
    'pausada': {'label': 'Pausada', 'color': '#9C27B0'}
}

STATUS_COLORS = {
    'pendente': {'cor': '#4e73df', 'cor_hover': '#2e59d9'},
    'andamento': {'cor': '#36b9cc', 'cor_hover': '#2c9faf'},
    'concluida': {'cor': '#1cc88a', 'cor_hover': '#17a673'},
    'cancelada': {'cor': '#e74a3b', 'cor_hover': '#d62d1f'},
    'pausada': {'cor': '#858796', 'cor_hover': '#6c757d'},
}

PRIORIDADE_COLORS = {
    'alta': {'cor': '#e74a3b', 'cor_hover': '#d62d1f'},
    'media': {'cor': '#f6c23e', 'cor_hover': '#e0a800'},
    'baixa': {'cor': '#1cc88a', 'cor_hover': '#17a673'},
}

User = get_user_model()


@login_required
def tarefas(request):
    """Lista todas as tarefas (para admin ou superusuário)"""
    if not request.user.is_superuser:
        return redirect('tarefas:listar_tarefas')
    
    tarefas = Tarefas.objects.all().order_by('-data_criacao')
    return render(request, 'tarefas/tarefas.html', {'tarefas': tarefas})

"""Cria uma nova tarefa"""
@login_required
def criar_tarefa(request):
    if request.method == 'POST':
        form = TarefaForm(request.POST)
        if form.is_valid():
            tarefa = form.save(commit=False)
            tarefa.usuario = request.user  # Define o usuário logado
            tarefa.save()
            messages.success(request, 'Tarefa criada com sucesso!')
            return redirect('tarefas:listar_tarefas')
    else:
        form = TarefaForm()
    
    return render(request, 'tarefas/criar_tarefa.html', {'form': form})

"""Edita uma tarefa existente"""
@login_required
def editar_tarefa(request, pk):
    tarefa = get_object_or_404(Tarefas, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        form = TarefaForm(request.POST, instance=tarefa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tarefa atualizada com sucesso!')
            return redirect('tarefas:tarefa_detail', pk=pk)
    else:
        form = TarefaForm(instance=tarefa)
    
    return render(request, 'tarefas/editar_tarefa.html', {
        'form': form,
        'tarefa': tarefa,
    })

@login_required
def excluir_tarefa(request, pk):
    """View para excluir uma tarefa com confirmação"""
    tarefa = get_object_or_404(Tarefas, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        try:
            tarefa.delete()
            logger.info(f'Tarefa {pk} excluída por {request.user}')
            messages.success(request, 'Tarefa excluída com sucesso!')
            return redirect('tarefas:listar_tarefas')
        except Exception as e:
            logger.error(f'Erro ao excluir tarefa {pk}: {str(e)}')
            messages.error(request, 'Erro ao excluir tarefa!')
            return redirect('tarefas:tarefa_detail', pk=pk)
    
    # Se for GET, mostrar página de confirmação
    return render(request, 'tarefas/confirmar_exclusao.html', {'tarefa': tarefa})

@login_required  # Garante que apenas usuários logados acessem o perfil
def profile_view(request):
    return render(request, 'usuario/profile.html')  # Renderiza o template do perfil

@login_required
def listar_tarefas(request):
    # Obter as choices diretamente do modelo
    status_choices = Tarefas.STATUS_CHOICES
    prioridade_choices = Tarefas.PRIORIDADE_CHOICES
    
    # Restante da lógica da view...
    tarefas = Tarefas.objects.all()
    
    return render(request, 'tarefas/listar_tarefas.html', {
        'tarefas': tarefas,
        'status_choices': status_choices,
        'prioridade_choices': prioridade_choices,
        # outros contextos...
    })

@login_required
def tarefa_detail(request, pk):
    """Detalhes de uma tarefa específica"""
    tarefa = get_object_or_404(Tarefas, pk=pk, usuario=request.user)
    comentarios = tarefa.comentarios.all().order_by('-criado_em')
    
    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.tarefa = tarefa
            comentario.autor = request.user
            comentario.save()
            messages.success(request, 'Comentário adicionado!')
            return redirect('tarefas:tarefa_detail', pk=pk)
    else:
        form = ComentarioForm()

    return render(request, 'tarefas/tarefa_detail.html', {
        'tarefa': tarefa,
        'form': form,
        'comentarios': comentarios,
    })

class TarefaUpdateView(UserPassesTestMixin, UpdateView):
    model = Tarefas
    form_class = TarefaForm
    
    def test_func(self):
        return self.get_object().usuario == self.request.user
    

@login_required
@require_POST  # Agora funcionará corretamente
def atualizar_status(request, pk):
    tarefa = get_object_or_404(Tarefas, pk=pk)
    novo_status = request.POST.get('status')
    
    if novo_status and novo_status != tarefa.status:
        # Registrar histórico antes de atualizar
        HistoricoStatus.objects.create(
            tarefa=tarefa,
            status_anterior=tarefa.status,
            novo_status=novo_status,
            alterado_por=request.user
        )
        
        # Atualizar status
        tarefa.status = novo_status
        tarefa.save()
        
        messages.success(request, f'Status da tarefa atualizado para {tarefa.get_status_display()}')
    
    return redirect('tarefas:tarefa_detail', pk=pk)

@login_required
def calendario_tarefas(request):
    tarefas = Tarefas.objects.all()
    eventos = []
    
    for tarefa in tarefas:
        eventos.append({
            'title': f"{tarefa.titulo} ({tarefa.get_prioridade_display()})",
            'start': tarefa.prazo.isoformat() if tarefa.prazo else None,
            'color': {
                'alta': '#ff4444',
                'media': '#ffbb33',
                'baixa': '#00C851'
            }.get(tarefa.prioridade, '#33b5e5'),
            'url': reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})
        })
    
    return render(request, 'tarefas/calendario.html', {
        'eventos': eventos
    })

@login_required
def relatorio_tarefas(request):
    """Gera relatório de tarefas com opção de exportação"""
    # Filtros
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    export_format = request.GET.get('export', '')

    # Query base - filtrando por usuário logado
    tarefas = Tarefas.objects.filter(usuario=request.user)

    # Aplicar filtros adicionais
    if status_filter:
        tarefas = tarefas.filter(status=status_filter)
    if date_from:
        tarefas = tarefas.filter(data_criacao__gte=date_from)
    if date_to:
        tarefas = tarefas.filter(data_criacao__lte=date_to)

    # Contagens por status
    status_counts = tarefas.values('status').annotate(count=Count('id'))
    total_tarefas = tarefas.count()
    
    # Preparar dados de status
    status_data = []
    chart_labels = []
    chart_data = []
    chart_colors = []
    
    for status_key, status_info in STATUS_MAP.items():
        count = next((item['count'] for item in status_counts if item['status'] == status_key), 0)
        percent = round((count / total_tarefas) * 100, 2) if total_tarefas > 0 else 0
        
        status_data.append({
            'key': status_key,
            'label': status_info['label'],
            'count': count,
            'percent': percent,
            'color': status_info['color']
        })
        
        chart_labels.append(status_info['label'])
        chart_data.append(count)
        chart_colors.append(status_info['color'])

    # Contexto comum
    context = {
        'tarefas': tarefas,
        'status_data': status_data,
        'total_tarefas': total_tarefas,
        'now': timezone.now(),
        'chart_data': {
            'labels': chart_labels,
            'data': chart_data,
            'colors': chart_colors
        },
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_map': {k: v['label'] for k, v in STATUS_MAP.items()},
    }

    # Exportação
    if export_format == 'pdf':
        return export_pdf(context)
    elif export_format == 'docx':
        return export_word(context)

    return render(request, 'tarefas/relatorio_tarefas.html', context)

def export_pdf(context):
    """Exporta relatório para PDF"""
    context['logo_path'] = 'midia/imagens/logo.png'  # Caminho para a logo  
    template = get_template('tarefas/relatorio_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    filename = f"relatorio_tarefas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF')
    return response

def export_word(context):
    """Exporta relatório para DOCX"""
    document = Document()
    
    # Cabeçalho
    # Adicionar logo
    logo_path = os.path.join(settings.BASE_DIR, 'midia', 'imagens', 'logo.png')
    if os.path.exists(logo_path):
        document.add_picture(logo_path, width=Inches(2.0))  # Ajuste o tamanho conforme necessár

    # Centralizar o título
    paragraph = document.add_paragraph()
    run = paragraph.add_run('Relatório de Tarefas')
    run.bold = True
    run.font.size = Pt(16)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph(f"Gerado em: {context['now'].strftime('%d/%m/%Y %H:%M')}")
    
    if context['date_from'] or context['date_to']:
        periodo = f"Período: {context['date_from'] or 'Início'} a {context['date_to'] or 'Hoje'}"
        document.add_paragraph(periodo)
    
    # Resumo
    document.add_heading('Resumo', level=1)
    table = document.add_table(rows=1, cols=3)
    table.style = 'LightShading-Accent1'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Status'
    hdr_cells[1].text = 'Quantidade'
    hdr_cells[2].text = 'Percentual'
    
    for status in context['status_data']:
        row_cells = table.add_row().cells
        row_cells[0].text = status['label']
        row_cells[1].text = str(status['count'])
        row_cells[2].text = f"{status['percent']}%"
    
    # Total
    row_cells = table.add_row().cells
    row_cells[0].text = 'TOTAL'
    row_cells[1].text = str(context['total_tarefas'])
    row_cells[2].text = '100%'
    
    # Detalhes
    document.add_heading('Detalhes das Tarefas', level=1)
    details_table = document.add_table(rows=1, cols=5)
    details_table.style = 'LightShading-Accent1'
    hdr_cells = details_table.rows[0].cells
    hdr_cells[0].text = 'Título'
    hdr_cells[1].text = 'Status'
    hdr_cells[2].text = 'Responsável'
    hdr_cells[3].text = 'Data Criação'
    hdr_cells[4].text = 'Prazo'
    
    for tarefa in context['tarefas']:
        row_cells = details_table.add_row().cells
        row_cells[0].text = tarefa.titulo
        row_cells[1].text = context['status_map'].get(tarefa.status, tarefa.status)
        row_cells[2].text = tarefa.responsavel.username if tarefa.responsavel else tarefa.usuario.username
        row_cells[3].text = tarefa.data_criacao.strftime('%d/%m/%Y')
        row_cells[4].text = tarefa.prazo.strftime('%d/%m/%Y') if tarefa.prazo else '-'
    
    # Salvar e retornar
    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    filename = f"relatorio_tarefas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def dashboard(request):
    """Painel de controle com métricas das tarefas"""
    # Consultas básicas
    total_tarefas = Tarefas.objects.filter(usuario=request.user).count()
    tarefas_concluidas = Tarefas.objects.filter(usuario=request.user, status='concluida').count()
    
    tarefas_atrasadas = Tarefas.objects.filter(
        usuario=request.user,
        prazo__lt=timezone.now().date(),
        status__in=['pendente', 'andamento', 'pausada']
    ).count()
    
    tarefas_andamento = Tarefas.objects.filter(usuario=request.user, status='andamento').count()
    
    # Distribuição por status
    status_dist = Tarefas.objects.filter(usuario=request.user).values('status').annotate(total=Count('id'))
    status_dist = [
        {
            'status': item['status'].capitalize(),
            'total': item['total'],
            'cor': STATUS_COLORS.get(item['status'], {}).get('cor', '#6c757d'),
            'cor_hover': STATUS_COLORS.get(item['status'], {}).get('cor_hover', '#5a6268')
        }
        for item in status_dist
    ]
    
    # Distribuição por prioridade
    prioridade_dist = Tarefas.objects.filter(usuario=request.user).values('prioridade').annotate(total=Count('id'))
    prioridade_dist = [
        {
            'prioridade': item['prioridade'].capitalize(),
            'total': item['total'],
            'cor': PRIORIDADE_COLORS.get(item['prioridade'], {}).get('cor', '#6c757d'),
            'cor_hover': PRIORIDADE_COLORS.get(item['prioridade'], {}).get('cor_hover', '#5a6268')
        }
        for item in prioridade_dist
    ]
    
    # Tarefas recentes
    tarefas_recentes = Tarefas.objects.filter(usuario=request.user).order_by('-data_criacao')[:10]
    
    context = {
        'total_tarefas': total_tarefas,
        'tarefas_concluidas': tarefas_concluidas,
        'tarefas_atrasadas': tarefas_atrasadas,
        'tarefas_andamento': tarefas_andamento,
        'status_dist': status_dist,
        'prioridade_dist': prioridade_dist,
        'tarefas_recentes': tarefas_recentes,
    }
    
    return render(request, 'tarefas/dashboard.html', context)

