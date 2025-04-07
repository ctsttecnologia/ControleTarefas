from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import TarefaForm  # Criaremos o formulário depois
from django.views.decorators.csrf import csrf_exempt, csrf_protect, requires_csrf_token
from .models import Tarefas

from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import csv
from datetime import datetime


@csrf_exempt
@csrf_protect
@requires_csrf_token


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