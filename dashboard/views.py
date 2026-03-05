# dashboard/views.py

"""
Views do Dashboard — refatoradas para usar services.py.
Toda lógica de queries está centralizada em dashboard.services.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .services import (
    get_metricas_geral,
    get_metricas_treinamentos,
    get_metricas_tarefas,
    get_metricas_epi,
    get_metricas_documentos,
    get_metricas_pgr,
    pgr_disponivel,
)


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

CYCLE_INTERVAL_MS = 15_000  # 15 segundos entre telas


# =====================================================================
# HELPERS (públicos — usados por outros apps)
# =====================================================================

def get_filial_ativa(user):
    """Retorna a filial ativa do usuário ou None.
    
    ⚠️ Função pública — importada por outros apps (ex: cliente.views).
    """
    return getattr(user, 'filial_ativa', None)


def render_erro_filial(request, mensagem=None):
    """
    Renderiza a página de erro de configuração.
    NUNCA redireciona — sempre renderiza (evita loops).
    
    ⚠️ Função pública — pode ser importada por outros apps.
    """
    messages.error(request, mensagem or "Nenhuma filial ativa definida para seu usuário.")
    return render(request, 'dashboard/erro_configuracao.html', {
        'title': 'Erro de Configuração',
    })


def _get_cycle_context(request, current_url_name):
    """Retorna o contexto de rotação automática do carrossel."""
    is_cycling = request.GET.get('cycle') == 'true'
    return {
        'is_cycling': is_cycling,
        'next_dashboard_url': DASHBOARD_CYCLE.get(current_url_name) if is_cycling else None,
        'cycle_interval': CYCLE_INTERVAL_MS,
        'current_dashboard': current_url_name,
    }


# =====================================================================
# VIEW: DASHBOARD GERAL
# =====================================================================

@login_required
def dashboard_geral_view(request):
    filial = get_filial_ativa(request.user)
    if not filial:
        return render_erro_filial(request)

    context = {
        'title': f'Visão Geral — {filial}',
        **get_metricas_geral(filial),
        **_get_cycle_context(request, 'dashboard:dashboard_geral'),
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

    context = {
        'title': 'Dashboard Treinamentos',
        **get_metricas_treinamentos(filial, dias_alerta=15),
        **_get_cycle_context(request, 'dashboard:dashboard_treinamentos'),
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

    context = {
        'title': 'Dashboard Tarefas',
        **get_metricas_tarefas(filial),
        **_get_cycle_context(request, 'dashboard:dashboard_tarefas'),
    }
    return render(request, 'dashboard/dashboard_tarefas.html', context)


# =====================================================================
# VIEW: DASHBOARD EPI
# =====================================================================

@login_required
def dashboard_epi_view(request):
    filial = get_filial_ativa(request.user)
    if not filial:
        return render_erro_filial(request)

    context = {
        'title': 'Dashboard EPI',
        **get_metricas_epi(filial),
        **_get_cycle_context(request, 'dashboard:dashboard_epi'),
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

    context = {
        'title': 'Dashboard Documentos',
        **get_metricas_documentos(filial, dias_alerta=30),
        **_get_cycle_context(request, 'dashboard:dashboard_documentos'),
    }
    return render(request, 'dashboard/dashboard_documentos.html', context)


# =====================================================================
# VIEW: DASHBOARD PGR
# =====================================================================

@login_required
def dashboard_pgr_view(request):
    if not pgr_disponivel():
        messages.error(request, "O módulo PGR não está disponível.")
        return render(request, 'dashboard/erro_configuracao.html', {
            'title': 'Erro de Configuração',
        })

    filial = get_filial_ativa(request.user)
    if not filial:
        return render_erro_filial(request)

    from django.utils import timezone
    metricas = get_metricas_pgr(filial)
    cycle_ctx = _get_cycle_context(request, 'dashboard:dashboard_pgr')

    context = {
        'title': 'Dashboard PGR',
        'hoje': timezone.now().date(),
        **metricas,
        **cycle_ctx,
    }

    template = (
        'dashboard/dashboard_pgr_fullscreen.html'
        if cycle_ctx['is_cycling']
        else 'dashboard/dashboard_pgr.html'
    )
    return render(request, template, context)
