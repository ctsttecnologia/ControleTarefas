# gestao_riscos/views.py

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages  # MUDANÇA 1: Import correto do messages
from django.utils import timezone
# Import dos seus forms e models
from .forms import IncidenteForm, InspecaoForm
from .models import Incidente, Inspecao


@login_required # MUDANÇA 4: Protegendo a view, só usuários logados podem acessar
def gestao_riscos(request):
    """
    View principal que exibe um dashboard de incidentes e inspeções.
    """
    # Busca os 10 incidentes mais recentes
    ultimos_incidentes = Incidente.objects.all().order_by('-data_ocorrencia')[:10]
    # Busca todas as inspeções com status 'PENDENTE'
    inspecoes_pendentes = Inspecao.objects.filter(status='PENDENTE').order_by('data_agendada')
        

    context = {
        'incidentes': ultimos_incidentes,
        'inspecoes': inspecoes_pendentes,
        'titulo_pagina': 'Dashboard de Gestão de Riscos',
        'data_atual': timezone.now(),
    }
    
    return render(request, 'gestao_riscos/lista_riscos.html', context)


@login_required
def registrar_incidente(request):
    """
    Processa o formulário para registrar um novo incidente.
    """
    # MUDANÇA 3: Estrutura padrão de view com formulário
    if request.method == 'POST':
        # Formulário preenchido com os dados enviados
        form = IncidenteForm(request.POST)
        if form.is_valid():
            incidente = form.save(commit=False) 
            incidente.registrado_por = request.user 
            incidente.save()
            
            # MUDANÇA 2: Mensagem de sucesso direta, sem a variável 'result'
            messages.success(request, 'Incidente registrado com sucesso!')
            return redirect('gestao_riscos:lista_riscos')
        else:
            # Se o formulário for inválido, exibe uma mensagem de erro
            messages.error(request, 'Por favor, corrija os erros no formulário.')
    else:
        # Se for um GET, exibe um formulário em branco
        form = IncidenteForm()

    context = {
        'form': form,
        'titulo_pagina': 'Registrar Novo Incidente',
        'botao_submit_texto': 'Registrar Incidente', # Texto para o botão de submit
    }
    # Renderiza o mesmo template genérico para GET e POST com erro
    return render(request, 'gestao_riscos/formulario_inspecao.html', context)


@login_required
def agendar_inspecao(request):
    """
    Processa o formulário para agendar uma nova inspeção.
    """
    if request.method == 'POST':
        form = InspecaoForm(request.POST)
        if form.is_valid():
            form.save() # O status 'PENDENTE' é o padrão no modelo.
            messages.success(request, 'Inspeção agendada com sucesso!')
            return redirect('gestao_riscos:lista_riscos')
        else:
            messages.error(request, 'Por favor, corrija os erros no formulário.')
    else:
        form = InspecaoForm()

    context = {
        'form': form,
        'titulo_pagina': 'Agendar Nova Inspeção',
        'botao_submit_texto': 'Agendar Inspeção', # Texto para o botão de submit
    }
    return render(request, 'gestao_riscos/formulario_inspecao.html', context)