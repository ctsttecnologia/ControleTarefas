# dashboard/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Value, IntegerField, Count, Q
from django.db.models.functions import Coalesce
from django.contrib import messages
import datetime
import json

from treinamentos.models import Treinamento, Participante
from tarefas.models import Tarefas
from seguranca_trabalho.models import Equipamento, EntregaEPI, MovimentacaoEstoque
from documentos.models import Documento

# PGR com fallback seguro
_PGR_AVAILABLE = False
try:
    from pgr_gestao.models import PGRDocumento, RiscoIdentificado, PlanoAcaoPGR, GESGrupoExposicao
    _PGR_AVAILABLE = True
except ImportError as e:
    print(f"Módulo PGR não disponível: {e}")
    PGRDocumento = RiscoIdentificado = PlanoAcaoPGR = GESGrupoExposicao = None


# =====================================================================
# CONFIGURAÇÃO DO CARROSSEL TV
# =====================================================================

DASHBOARD_CYCLE = {
    'dashboard:dashboard_geral':        'dashboard:dashboard_treinamentos',
    'dashboard:dashboard_treinamentos': 'dashboard:dashboard_tarefas',
    'dashboard:dashboard_tarefas':      'dashboard:dashboard_epi',
    'dashboard:dashboard_epi':          'dashboard:dashboard_documentos',
    'dashboard:dashboard_documentos':   'dashboard:dashboard_pgr',
    'dashboard:dashboard_pgr':          'dashboard:dashboard_geral',
}

CYCLE_INTERVAL_MS = 15000  # 15 segundos entre telas


def get_cycle_context(request, current_url_name):
    """
    Retorna o contexto de rotação automática do carrossel.
    Se ?cycle=true estiver na URL, o template faz auto-redirect após X segundos.
    """
    is_cycling = request.GET.get('cycle') == 'true'
    next_url = DASHBOARD_CYCLE.get(current_url_name) if is_cycling else None

    return {
        'is_cycling': is_cycling,
        'next_dashboard_url': next_url,
        'cycle_interval': CYCLE_INTERVAL_MS,
        'current_dashboard': current_url_name,
    }


# =====================================================================
# FUNÇÕES AUXILIARES
# =====================================================================

def get_filial_ativa(user):
    """Retorna a filial ativa do usuário ou None."""
    return getattr(user, 'filial_ativa', None)


def render_erro_filial(request, mensagem=None):
    """
    Renderiza a página de erro de configuração de forma consistente.
    NUNCA redireciona — sempre renderiza (evita loops de redirect).
    """
    msg = mensagem or "Nenhuma filial ativa definida para seu usuário."
    messages.error(request, msg)
    return render(request, 'dashboard/erro_configuracao.html', {
        'title': 'Erro de Configuração',
    })


# =====================================================================
# VIEW: DASHBOARD GERAL
# =====================================================================

@login_required
def dashboard_geral_view(request):
    filial = get_filial_ativa(request.user)
    if not filial:
        return render_erro_filial(request)

    hoje = timezone.now().date()

    treinamentos_vencimento_proximo = Treinamento.objects.filter(
        filial=filial,
        data_vencimento__gte=hoje,
        data_vencimento__lte=hoje + datetime.timedelta(days=15)
    ).count()

    tarefas_atrasadas = Tarefas.objects.filter(
        filial=filial,
        prazo__lt=timezone.now(),
        status__in=['pendente', 'andamento', 'pausada']
    ).count()

    entregas_sem_assinatura = EntregaEPI.objects.filter(
        Q(assinatura_recebimento='') | Q(assinatura_recebimento__isnull=True),
        Q(assinatura_imagem__isnull=True),
        filial=filial,
    ).count()

    documentos_a_vencer = Documento.objects.filter(
        filial=filial,
        data_vencimento__gte=hoje,
        data_vencimento__lte=hoje + datetime.timedelta(days=30)
    ).count()

    # Alertas críticos
    alertas = []
    if treinamentos_vencimento_proximo > 0:
        alertas.append({
            'tipo': 'danger',
            'msg': f'{treinamentos_vencimento_proximo} treinamento(s) vencendo em 15 dias',
            'icon': 'fas fa-graduation-cap',
        })
    if tarefas_atrasadas > 0:
        alertas.append({
            'tipo': 'danger',
            'msg': f'{tarefas_atrasadas} tarefa(s) atrasada(s)',
            'icon': 'fas fa-tasks',
        })
    if entregas_sem_assinatura > 0:
        alertas.append({
            'tipo': 'warning',
            'msg': f'{entregas_sem_assinatura} EPI(s) sem assinatura',
            'icon': 'fas fa-signature',
        })
    if documentos_a_vencer > 0:
        alertas.append({
            'tipo': 'warning',
            'msg': f'{documentos_a_vencer} documento(s) vencendo em 30 dias',
            'icon': 'fas fa-file-alt',
        })

    context = {
        'title': f'Visão Geral — {filial}',
        'total_treinamentos': Treinamento.objects.filter(filial=filial).count(),
        'total_tarefas': Tarefas.objects.filter(filial=filial).count(),
        'total_entregas_epi': EntregaEPI.objects.filter(filial=filial).count(),
        'total_documentos': Documento.objects.filter(filial=filial).count(),
        'treinamentos_vencimento_proximo': treinamentos_vencimento_proximo,
        'tarefas_atrasadas': tarefas_atrasadas,
        'entregas_sem_assinatura': entregas_sem_assinatura,
        'documentos_a_vencer': documentos_a_vencer,
        'alertas_criticos': alertas,
        **get_cycle_context(request, 'dashboard:dashboard_geral'),
    }
    return render(request, 'dashboard/dashboard_geral.html', context)


# =====================================================================
# VIEW: DASHBOARD TREINAMENTOS
# =====================================================================

@login_required
def dashboard_treinamentos_view(request):
    filial = get_filial_ativa(request.user)
    if not filial:
        return render_erro_filial(request)

    hoje = timezone.now().date()
    qs = Treinamento.objects.filter(filial=filial)

    vencidos = qs.filter(data_vencimento__lt=hoje).count()
    a_vencer = qs.filter(
        data_vencimento__gte=hoje,
        data_vencimento__lte=hoje + datetime.timedelta(days=15)
    ).count()

    participantes = Participante.objects.filter(funcionario__filial_ativa=filial)
    total_part = participantes.count()
    presenca = (participantes.filter(presente=True).count() / total_part * 100) if total_part > 0 else 0

    context = {
        'title': 'Dashboard Treinamentos',
        'total_treinamentos': qs.count(),
        'status_data': list(qs.values('status').annotate(total=Count('id'))),
        'vencidos': vencidos,
        'vencimento_proximo': a_vencer,
        'taxa_presenca': round(presenca, 1),
        'total_participantes': total_part,
        'proximos_treinamentos': qs.filter(data_inicio__gte=hoje).order_by('data_inicio')[:5],
        **get_cycle_context(request, 'dashboard:dashboard_treinamentos'),
    }
    return render(request, 'dashboard/dashboard_treinamentos.html', context)


# =====================================================================
# VIEW: DASHBOARD TAREFAS
# =====================================================================

@login_required
def dashboard_tarefas_view(request):
    filial = get_filial_ativa(request.user)
    if not filial:
        return render_erro_filial(request)

    qs = Tarefas.objects.filter(filial=filial)
    total = qs.count()
    atrasadas = qs.filter(
        prazo__lt=timezone.now(),
        status__in=['pendente', 'andamento']
    ).count()
    progresso_medio = sum(t.progresso for t in qs) / total if total > 0 else 0

    context = {
        'title': 'Dashboard Tarefas',
        'total_tarefas': total,
        'status_data': list(qs.values('status').annotate(total=Count('id'))),
        'prioridade_data': list(qs.values('prioridade').annotate(total=Count('id'))),
        'tarefas_atrasadas': atrasadas,
        'progresso_medio': round(progresso_medio, 1),
        'tarefas_proximas': qs.filter(prazo__gte=timezone.now()).order_by('prazo')[:6],
        **get_cycle_context(request, 'dashboard:dashboard_tarefas'),
    }
    return render(request, 'dashboard/dashboard_tarefas.html', context)


# =====================================================================
# VIEW: DASHBOARD EPI  ← ERA AQUI O PROBLEMA PRINCIPAL
# =====================================================================

@login_required
def dashboard_epi_view(request):
    filial = get_filial_ativa(request.user)
    if not filial:
        return render_erro_filial(request)

    hoje = timezone.now().date()
    limite_aviso = hoje + datetime.timedelta(days=30)

    # ── Entregas ──
    entregas = EntregaEPI.objects.filter(filial=filial).select_related('equipamento')
    entregas_vencimento_proximo = 0

    for entrega in entregas:
        if entrega.data_entrega and entrega.equipamento and entrega.equipamento.vida_util_dias:
            vencimento = entrega.data_entrega + datetime.timedelta(days=entrega.equipamento.vida_util_dias)
            if hoje <= vencimento <= limite_aviso:
                entregas_vencimento_proximo += 1

    # ── Movimentações ──
    mov = MovimentacaoEstoque.objects.filter(filial=filial)

    total_entradas = mov.filter(tipo='ENTRADA').aggregate(
        total=Coalesce(Sum('quantidade'), Value(0, output_field=IntegerField()))
    )['total']

    total_saidas = mov.filter(tipo='SAIDA').aggregate(
        total=Coalesce(Sum('quantidade'), Value(0, output_field=IntegerField()))
    )['total']

    movimentacoes_recentes = mov.select_related(
        'equipamento', 'responsavel'
    ).order_by('-data')[:10]

    # ── Equipamentos e Estoque Crítico ──
    equipamentos = Equipamento.objects.filter(filial=filial, ativo=True)
    baixo_estoque = []
    resumo_equipamentos = []

    for eq in equipamentos:
        entradas = mov.filter(equipamento=eq, tipo='ENTRADA').aggregate(
            total=Coalesce(Sum('quantidade'), Value(0, output_field=IntegerField()))
        )['total']
        saidas = mov.filter(equipamento=eq, tipo='SAIDA').aggregate(
            total=Coalesce(Sum('quantidade'), Value(0, output_field=IntegerField()))
        )['total']
        estoque_atual = entradas - saidas

        resumo_equipamentos.append({
            'nome': eq.nome,
            'entradas': entradas,
            'saidas': saidas,
            'atual': estoque_atual,
            'min': eq.estoque_minimo,
            'status': (
                'critico' if estoque_atual <= eq.estoque_minimo
                else 'alerta' if estoque_atual <= eq.estoque_minimo + 10
                else 'ok'
            ),
        })

        if estoque_atual <= eq.estoque_minimo:
            baixo_estoque.append({
                'nome': eq.nome,
                'atual': estoque_atual,
                'min': eq.estoque_minimo,
            })

    # ══════════════════════════════════════════════════════════════════
    #  ✅ FIX: Adicionado get_cycle_context que estava faltando!
    # ══════════════════════════════════════════════════════════════════
    context = {
        'title': 'Dashboard EPI',
        'total_entregas': entregas.count(),
        'entregas_sem_assinatura': entregas.filter(
            Q(assinatura_recebimento='') | Q(assinatura_recebimento__isnull=True),
            Q(assinatura_imagem__isnull=True),
        ).count(),
        'entregas_vencimento_proximo': entregas_vencimento_proximo,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'equipamentos_estoque_baixo': baixo_estoque,
        'resumo_equipamentos': resumo_equipamentos,
        'movimentacoes_recentes': movimentacoes_recentes,
        **get_cycle_context(request, 'dashboard:dashboard_epi'),  # ← ESTAVA FALTANDO!
    }
    return render(request, 'dashboard/dashboard_epi.html', context)


# =====================================================================
# VIEW: DASHBOARD DOCUMENTOS
# =====================================================================

@login_required
def dashboard_documentos_view(request):
    filial = get_filial_ativa(request.user)
    if not filial:
        return render_erro_filial(request)

    hoje = timezone.now().date()
    qs = Documento.objects.filter(filial=filial)

    context = {
        'title': 'Dashboard Documentos',
        'total_documentos': qs.count(),
        'status_data': list(qs.values('status').annotate(total=Count('id'))),
        'documentos_vencidos': qs.filter(data_vencimento__lt=hoje).count(),
        'documentos_a_vencer': qs.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + datetime.timedelta(days=30)
        ).count(),
        'proximos_vencimentos': qs.filter(data_vencimento__gte=hoje).order_by('data_vencimento')[:6],
        **get_cycle_context(request, 'dashboard:dashboard_documentos'),
    }
    return render(request, 'dashboard/dashboard_documentos.html', context)


# =====================================================================
# VIEW: DASHBOARD PGR
# =====================================================================

@login_required
def dashboard_pgr_view(request):
    if not _PGR_AVAILABLE:
        messages.error(request, "O módulo PGR não está disponível.")
        return render(request, 'dashboard/erro_configuracao.html', {'title': 'Erro de Configuração'})

    filial = get_filial_ativa(request.user)
    if not filial:
        return render_erro_filial(request)

    hoje = timezone.now().date()

    documentos = PGRDocumento.objects.filter(empresa__filial=filial)
    riscos = RiscoIdentificado.objects.filter(pgr_documento__empresa__filial=filial)
    planos = PlanoAcaoPGR.objects.filter(risco_identificado__pgr_documento__empresa__filial=filial)
    gess = GESGrupoExposicao.objects.filter(filial=filial)

    # Documentos: vigência
    docs_vigentes = documentos.filter(data_vencimento__gte=hoje).count()
    docs_vencidos = documentos.filter(data_vencimento__lt=hoje).count()
    docs_a_vencer = list(
        documentos.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + datetime.timedelta(days=30)
        ).order_by('data_vencimento')
    )

    # Riscos críticos
    riscos_criticos = riscos.filter(
        classificacao_risco__in=['critico', 'muito_grave'],
        status_controle__in=['identificado', 'em_controle']
    )

    # Planos
    planos_pendentes = planos.filter(status__in=['pendente', 'em_andamento']).count()
    planos_atrasados = planos.filter(
        data_prevista__lt=hoje,
        status__in=['pendente', 'em_andamento']
    ).count()

    # Dados para Chart.js
    riscos_classificacao = list(
        riscos.values('classificacao_risco').annotate(total=Count('id')).order_by('classificacao_risco')
    )
    riscos_status = list(
        riscos.values('status_controle').annotate(total=Count('id'))
    )

    cycle_ctx = get_cycle_context(request, 'dashboard:dashboard_pgr')

    context = {
        'title': 'Dashboard PGR',
        'hoje': hoje,
        'total_documentos': documentos.count(),
        'documentos_vigentes': docs_vigentes,
        'documentos_vencidos': docs_vencidos,
        'riscos_criticos': riscos_criticos,
        'total_riscos': riscos.count(),
        'planos_pendentes': planos_pendentes,
        'planos_atrasados': planos_atrasados,
        'total_ges': gess.count(),
        'documentos_proximo_vencimento': docs_a_vencer,
        'riscos_por_classificacao': json.dumps(riscos_classificacao),
        'riscos_por_status': json.dumps(riscos_status),
        'ultimas_revisoes': documentos.order_by('-atualizado_em')[:5],
        'ultimos_planos': planos.order_by('-criado_em')[:5],
        **cycle_ctx,
    }

    template = (
        'dashboard/dashboard_pgr_fullscreen.html'
        if cycle_ctx['is_cycling']
        else 'dashboard/dashboard_pgr.html'
    )
    return render(request, template, context)

