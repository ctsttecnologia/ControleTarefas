from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt, csrf_protect, requires_csrf_token


from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import csv
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Count, Q
from datetime import datetime, timedelta
from .models import Tarefas, Comentario, HistoricoStatus
from .forms import TarefaForm, ComentarioForm
from django.views.decorators.http import require_POST
from django.contrib import messages





@login_required # retrição de autenticação
def tarefas(request):
    tarefas = Tarefas.objects.all().order_by('-data_criacao')
    return render(request, 'tarefas/tarefas.html', {'tarefas': tarefas})

@login_required # retrição de autenticação
def tarefas(request):
    return render(request, 'tarefas/tarefas.html')

@login_required  # Garante que apenas usuários logados acessem o perfil
def criar_tarefa(request):
    if request.method == 'POST':
        form = TarefaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('consultar_tarefa')
    else:
        form = TarefaForm()
    return render(request, 'tarefas/criar_tarefa.html', {'form': form})

@login_required  # Garante que apenas usuários logados acessem o perfil
def editar_tarefa(request, id):
    tarefas = get_object_or_404(Tarefas, id=id)
    if request.method == 'POST':
        form = TarefaForm(request.POST, instance=tarefas)
        if form.is_valid():
            form.save()
            return redirect('consultar_tarefa')
    else:
        form = TarefaForm(instance=tarefas)
    return render(request, 'tarefas/editar_tarefa.html', {'form': form})

@login_required  # Garante que apenas usuários logados acessem o perfil
def excluir_tarefa(request, id):
    tarefa = get_object_or_404(Tarefa, id=id)
    if request.method == 'POST':
        tarefa.delete()
        return redirect('consultar_tarefa')
    return render(request, 'tarefas/confirmar_exclusao.html', {'tarefa': tarefas})

@login_required  # Garante que apenas usuários logados acessem o perfil
def profile_view(request):
    return render(request, 'usuario/profile.html')  # Renderiza o template do perfil

@login_required
def relatorio_tarefas(request):
    # Contagem de tarefas por status
    total_tarefas = Tarefas.objects.count()
    resolvidas = Tarefas.objects.filter(status='resolvida').count()
    pendentes = Tarefas.objects.filter(status='pendente').count()
    em_andamento = Tarefas.objects.filter(status='em_andamento').count()
    
    context = {
        'total_tarefas': total_tarefas,
        'resolvidas': resolvidas,
        'pendentes': pendentes,
        'em_andamento': em_andamento,
    }
    return render(request, 'relatorio_tarefas.html', context)
@login_required
def relatorio_tarefas(request):
    # Filtros
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Query base
    tarefas = Tarefas.objects.all()

    # Aplicar filtros
    if status_filter:
        tarefas = tarefas.filter(status=status_filter)
    
    if date_from:
        tarefas = tarefas.filter(data_criacao__gte=date_from)
    
    if date_to:
        tarefas = tarefas.filter(data_criacao__lte=date_to)

    # Contagens por status
    contagens = {
        'total': tarefas.count(),
        'resolvidas': tarefas.filter(status='resolvida').count(),
        'pendentes': tarefas.filter(status='pendente').count(),
        'em_andamento': tarefas.filter(status='em_andamento').count(),
    }

    # Dados para gráfico
    chart_data = {
        'labels': ['Resolvidas', 'Pendentes', 'Em Andamento'],
        'data': [
            contagens['resolvidas'],
            contagens['pendentes'],
            contagens['em_andamento']
        ],
        'colors': ['#4CAF50', '#FFC107', '#2196F3']
    }

    context = {
        'tarefas': tarefas,
        'contagens': contagens,
        'chart_data': chart_data,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    }

    # Exportação
    export_format = request.GET.get('export', '')
    if export_format == 'pdf':
        return export_pdf(context)
    elif export_format == 'csv':
        return export_csv(tarefas)

    return render(request, 'relatorio_tarefas.html', context)
@login_required
def export_pdf(context):
    template = get_template('relatorio_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_tarefas.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF')
    return response
@login_required
def export_csv(queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_tarefas.csv"'

    writer = csv.writer(response)
    writer.writerow(['Título', 'Responsável', 'Status', 'Criação', 'Prazo'])

    for tarefa in queryset:
        writer.writerow([
            tarefa.titulo,
            tarefa.nome,
            tarefa.get_status_display(),
            tarefa.data_criacao.strftime('%d/%m/%Y'),
            tarefa.prazo.strftime('%d/%m/%Y') if tarefa.prazo else ''
        ])

    return response

@login_required
def dashboard(request):
    # Filtros
    status_filter = request.GET.get('status', '')
    prioridade_filter = request.GET.get('prioridade', '')
    usuario_filter = request.GET.get('usuario', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Query base
    tarefas = Tarefas.objects.all()

    # Aplicar filtros
    if status_filter:
        tarefas = tarefas.filter(status=status_filter)
    if prioridade_filter:
        tarefas = tarefas.filter(prioridade=prioridade_filter)
    if usuario_filter:
        tarefas = tarefas.filter(usuario__id=usuario_filter)
    if date_from:
        tarefas = tarefas.filter(data_criacao__gte=date_from)
    if date_to:
        tarefas = tarefas.filter(data_criacao__lte=date_to)

    # Métricas
    total_tarefas = tarefas.count()
    tarefas_resolvidas = tarefas.filter(status='resolvida').count()
    tarefas_atrasadas = tarefas.filter(
        prazo__lt=datetime.now().date(),
        status__in=['pendente', 'em_andamento']
    ).count()

    # Distribuição por status
    status_dist = tarefas.values('status').annotate(total=Count('id'))

    # Distribuição por prioridade
    prioridade_dist = tarefas.values('prioridade').annotate(total=Count('id'))

    # Tarefas por usuário
    usuario_dist = tarefas.values('usuario__username').annotate(total=Count('id'))

    # Próximos prazos
    proximos_prazos = tarefas.filter(
        prazo__gte=datetime.now().date(),
        status__in=['pendente', 'em_andamento']
    ).order_by('prazo')[:5]

    context = {
        'tarefas': tarefas,
        'total_tarefas': total_tarefas,
        'tarefas_resolvidas': tarefas_resolvidas,
        'tarefas_atrasadas': tarefas_atrasadas,
        'status_dist': list(status_dist),
        'prioridade_dist': list(prioridade_dist),
        'usuario_dist': list(usuario_dist),
        'proximos_prazos': proximos_prazos,
        'usuarios': User.objects.all(),
    }

    return render(request, 'tarefas/dashboard.html', context)

@login_required
def tarefa_detail(request, pk):
    tarefa = get_object_or_404(Tarefas, pk=pk)
    
    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.tarefa = tarefa
            comentario.autor = request.user
            comentario.save()
            return redirect('tarefa-detail', pk=pk)
    else:
        form = ComentarioForm()

    return render(request, 'tarefas/tarefa_detail.html', {
        'tarefa': tarefa,
        'form': form,
    })

@login_required
@require_POST
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
        
        # Enviar notificação (implementar lógica de notificação)
        messages.success(request, f'Status da tarefa atualizado para {tarefa.get_status_display()}')
    
    return redirect('tarefa-detail', pk=pk)

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
            'url': reverse('tarefa-detail', kwargs={'pk': tarefa.pk})
        })
    
    return render(request, 'tarefas/calendario.html', {
        'eventos': eventos
    })

