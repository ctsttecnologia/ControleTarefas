from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib import messages
import datetime

# Importações dentro de try/except para evitar erros de migração
try:
    from treinamentos.models import Treinamento, Participante
    from tarefas.models import Tarefas
    from seguranca_trabalho.models import Equipamento, EntregaEPI, MovimentacaoEstoque
    from documentos.models import Documento
except ImportError:
    pass

# --- CONFIGURAÇÃO DO MODO TV (CARROSSEL) ---
DASHBOARD_CYCLE = {
    'dashboard:dashboard_geral': 'dashboard:dashboard_treinamentos',
    'dashboard:dashboard_treinamentos': 'dashboard:dashboard_tarefas',
    'dashboard:dashboard_tarefas': 'dashboard:dashboard_epi',
    'dashboard:dashboard_epi': 'dashboard:dashboard_documentos',
    'dashboard:dashboard_documentos': 'dashboard:dashboard_geral',
}

def get_cycle_context(request, current_url_name):
    """
    Gerencia a lógica de rotação automática.
    """
    is_cycling = request.GET.get('cycle') == 'true'
    next_url = DASHBOARD_CYCLE.get(current_url_name) if is_cycling else None
    
    return {
        'is_cycling': is_cycling,
        'next_dashboard_url': next_url,
        'cycle_interval': 15000, 
    }

# --- FUNÇÃO AUXILIAR PARA SEGURANÇA ---
def get_filial_ativa(user):
    # Ajuste este atributo conforme seu modelo de Usuário/Funcionário
    # Ex: return user.funcionario.filial_ativa
    if hasattr(user, 'filial_ativa'):
        return user.filial_ativa
    # Caso o usuário não tenha filial definida (ex: admin global), decida a lógica.
    # Aqui retornamos None, o que pode exigir tratamento nas views ou retornar erro.
    return None 

@login_required
def dashboard_geral_view(request):
    filial = get_filial_ativa(request.user)
    if not filial:
        # Tratamento de erro se o usuário não tiver filial
        messages.error(request, "Usuário sem filial ativa definida.")
        return render(request, 'dashboard/erro_configuracao.html')

    hoje = timezone.now().date()
    
    # --- Consultas Otimizadas com FILTRO DE FILIAL ---
    treinamentos_vencimento_proximo = Treinamento.objects.filter(
        filial=filial,  # <--- SEGURANÇA
        data_vencimento__gte=hoje,
        data_vencimento__lte=hoje + datetime.timedelta(days=15)
    ).count()
    
    tarefas_atrasadas = Tarefas.objects.filter(
        filial=filial,  # <--- SEGURANÇA
        prazo__lt=timezone.now(),
        status__in=['pendente', 'andamento', 'pausada']
    ).count()
    
    entregas_sem_assinatura = EntregaEPI.objects.filter(
        
        Q(assinatura_recebimento='') | Q(assinatura_recebimento__isnull=True), 
        Q(assinatura_imagem__isnull=True),

        filial=filial,  # <--- SEGURANÇA
    ).count()
    
    documentos_a_vencer = Documento.objects.filter(
        filial=filial,  # <--- SEGURANÇA
        data_vencimento__gte=hoje,
        data_vencimento__lte=hoje + datetime.timedelta(days=30)
    ).count()
    
    alertas = []
    if treinamentos_vencimento_proximo > 0:
        alertas.append({'tipo': 'danger', 'msg': f'{treinamentos_vencimento_proximo} treinamentos vencendo', 'icon': 'fas fa-graduation-cap'})
    if tarefas_atrasadas > 0:
        alertas.append({'tipo': 'danger', 'msg': f'{tarefas_atrasadas} tarefas atrasadas', 'icon': 'fas fa-tasks'})
    if entregas_sem_assinatura > 0:
        alertas.append({'tipo': 'warning', 'msg': f'{entregas_sem_assinatura} EPIs sem assinatura', 'icon': 'fas fa-signature'})
    
    context = {
        'title': f'Visão Geral - {filial}', # Mostra a filial no título
        'total_treinamentos': Treinamento.objects.filter(filial=filial).count(),
        'total_tarefas': Tarefas.objects.filter(filial=filial).count(),
        'total_entregas_epi': EntregaEPI.objects.filter(filial=filial).count(),
        'total_documentos': Documento.objects.filter(filial=filial).count(),
        'treinamentos_vencimento_proximo': treinamentos_vencimento_proximo,
        'tarefas_atrasadas': tarefas_atrasadas,
        'entregas_sem_assinatura': entregas_sem_assinatura,
        'documentos_a_vencer': documentos_a_vencer,
        'alertas_criticos': alertas,
        **get_cycle_context(request, 'dashboard:dashboard_geral')
    }
    return render(request, 'dashboard/dashboard_geral.html', context)

@login_required
def dashboard_treinamentos_view(request):
    filial = get_filial_ativa(request.user)
    if not filial: 
        return render(request, 'dashboard/erro_configuracao.html')

    hoje = timezone.now().date()
    
    # 1. Filtra os Treinamentos da filial
    qs = Treinamento.objects.filter(filial=filial)
    
    vencidos = qs.filter(data_vencimento__lt=hoje).count()
    a_vencer = qs.filter(data_vencimento__gte=hoje, data_vencimento__lte=hoje + datetime.timedelta(days=15)).count()
    
    # 2. Filtra Participantes pela filial ativa do Usuário
    # Caminho: Participante -> Funcionario (Usuario) -> Filial Ativa
    participantes = Participante.objects.filter(funcionario__filial_ativa=filial)
    
    total_part = participantes.count()
    
    # Cálculo de presença seguro
    presenca = (participantes.filter(presente=True).count() / total_part * 100) if total_part > 0 else 0
    
    context = {
        'title': 'Dashboard Treinamentos',
        'total_treinamentos': qs.count(),
        'status_data': qs.values('status').annotate(total=Count('id')),
        'vencidos': vencidos,
        'vencimento_proximo': a_vencer,
        'taxa_presenca': round(presenca, 1),
        'total_participantes': total_part,
        'proximos_treinamentos': qs.filter(data_inicio__gte=hoje).order_by('data_inicio')[:5],
        **get_cycle_context(request, 'dashboard:dashboard_treinamentos')
    }
    return render(request, 'dashboard/dashboard_treinamentos.html', context)

@login_required
def dashboard_tarefas_view(request):
    filial = get_filial_ativa(request.user)
    if not filial: return redirect('dashboard:erro')

    # Filtra tarefas da filial
    qs = Tarefas.objects.filter(filial=filial)
    total = qs.count()
    
    atrasadas = qs.filter(prazo__lt=timezone.now(), status__in=['pendente', 'andamento']).count()
    progresso_medio = sum(t.progresso for t in qs) / total if total > 0 else 0
    
    context = {
        'title': 'Dashboard Tarefas',
        'total_tarefas': total,
        'status_data': qs.values('status').annotate(total=Count('id')),
        'prioridade_data': qs.values('prioridade').annotate(total=Count('id')),
        'tarefas_atrasadas': atrasadas,
        'progresso_medio': round(progresso_medio, 1),
        'tarefas_proximas': qs.filter(prazo__gte=timezone.now()).order_by('prazo')[:6],
        **get_cycle_context(request, 'dashboard:dashboard_tarefas')
    }
    return render(request, 'dashboard/dashboard_tarefas.html', context)

@login_required
def dashboard_epi_view(request):
    filial = get_filial_ativa(request.user)
    if not filial: return redirect('dashboard:erro')

    hoje = timezone.now().date()
    
    # CORREÇÃO DE SEGURANÇA: Filtrar entregas da filial
    entregas = EntregaEPI.objects.filter(filial=filial).select_related('equipamento')
    
    entregas_vencimento_proximo = 0
    limite_aviso = hoje + datetime.timedelta(days=30)
    
    for entrega in entregas:
        if entrega.data_entrega and entrega.equipamento.vida_util_dias:
            vencimento = entrega.data_entrega + datetime.timedelta(days=entrega.equipamento.vida_util_dias)
            if hoje <= vencimento <= limite_aviso:
                entregas_vencimento_proximo += 1

    # Lógica de estoque -> O cálculo deve considerar apenas movimentações DA FILIAL
    # Se o Equipamento for cadastro global (mesmo CA para todas as filiais), mantemos Equipamento.objects.all()
    # Mas a contagem de entrada/saida TEM que ser filtrada pela filial.
    
    mov = MovimentacaoEstoque.objects.filter(filial=filial) # <--- O pulo do gato para o estoque não vazar
    
    # Se quiser mostrar apenas equipamentos que já tiveram movimentação na filial, altere para filtrar ids.
    # Assumindo aqui que queremos monitorar todo o catálogo possível:
    equipamentos = Equipamento.objects.all() 
    baixo_estoque = []
    
    for eq in equipamentos:
        # Filtra as movimentações da query JÁ filtrada por filial acima
        ent = mov.filter(equipamento=eq, tipo='ENTRADA').count()
        sai = mov.filter(equipamento=eq, tipo='SAIDA').count()
        atual = ent - sai
        
        # Só adiciona no alerta se tiver estoque baixo E (opcionalmente) se houver algum histórico nessa filial
        # Se quiser mostrar zerados que nunca entraram, mantenha a lógica abaixo.
        if atual <= eq.estoque_minimo:
            # Dica visual: mostrar estoque baixo apenas se a filial realmente usa esse item (ent > 0)
            if ent > 0 or atual < 0: 
                baixo_estoque.append({'nome': eq.nome, 'atual': atual, 'min': eq.estoque_minimo})

    context = {
        'title': 'Dashboard EPI',
        'total_entregas': entregas.count(),
        'total_equipamentos': equipamentos.count(), # Catálogo geral
        'entregas_sem_assinatura': entregas.filter(assinatura_recebimento__isnull=True).count(),
        'entregas_vencimento_proximo': entregas_vencimento_proximo,
        'total_entradas': mov.filter(tipo='ENTRADA').count(),
        'total_saidas': mov.filter(tipo='SAIDA').count(),
        'equipamentos_estoque_baixo': baixo_estoque,
        **get_cycle_context(request, 'dashboard:dashboard_epi')
    }
    return render(request, 'dashboard/dashboard_epi.html', context)

@login_required
def dashboard_documentos_view(request):
    filial = get_filial_ativa(request.user)
    if not filial: return redirect('dashboard:erro')

    hoje = timezone.now().date()
    
    # Filtra Documentos da filial
    qs = Documento.objects.filter(filial=filial)
    
    context = {
        'title': 'Dashboard Documentos',
        'total_documentos': qs.count(),
        'status_data': qs.values('status').annotate(total=Count('id')),
        'documentos_vencidos': qs.filter(data_vencimento__lt=hoje).count(),
        'documentos_a_vencer': qs.filter(data_vencimento__gte=hoje, data_vencimento__lte=hoje + datetime.timedelta(days=30)).count(),
        'proximos_vencimentos': qs.filter(data_vencimento__gte=hoje).order_by('data_vencimento')[:6],
        **get_cycle_context(request, 'dashboard:dashboard_documentos')
    }
    return render(request, 'dashboard/dashboard_documentos.html', context)