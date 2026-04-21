# dashboard/views.py

"""
Views do Dashboard — CBV com permissões granulares.
Toda lógica de queries está centralizada em dashboard.services.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import TemplateView

from core.mixins import AppPermissionMixin

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
# HELPERS PÚBLICOS (usados por outros apps)
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


# =====================================================================
# BASE VIEW: LÓGICA COMUM DE TODOS OS DASHBOARDS
# =====================================================================

class BaseDashboardView(LoginRequiredMixin, AppPermissionMixin, TemplateView):
    """
    View base para todos os dashboards.
    
    Subclasses devem definir:
    - template_name: caminho do template
    - permission_required: permissão específica do dashboard
    - dashboard_url_name: nome da URL (ex: 'dashboard:dashboard_geral')
    - title: título da página
    - get_metricas(filial): método que retorna dict de métricas
    """
    app_label_required = 'dashboard'  # fallback — mas usamos permission_required específica
    dashboard_url_name = None
    title = None

    def get_metricas(self, filial):
        """Sobrescrever nas subclasses — retorna dict de métricas."""
        raise NotImplementedError(
            f"{self.__class__.__name__} deve implementar get_metricas(filial)."
        )

    def get_cycle_context(self):
        """Retorna o contexto de rotação automática do carrossel."""
        is_cycling = self.request.GET.get('cycle') == 'true'
        return {
            'is_cycling': is_cycling,
            'next_dashboard_url': (
                DASHBOARD_CYCLE.get(self.dashboard_url_name) if is_cycling else None
            ),
            'cycle_interval': CYCLE_INTERVAL_MS,
            'current_dashboard': self.dashboard_url_name,
        }

    def dispatch(self, request, *args, **kwargs):
        """Verifica filial ativa ANTES de processar a view."""
        # ⚠️ LoginRequiredMixin + AppPermissionMixin já rodaram aqui
        # Mas só se o user estiver autenticado é que faz sentido checar filial
        if request.user.is_authenticated:
            self.filial = get_filial_ativa(request.user)
            if not self.filial:
                return render_erro_filial(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.get_title()
        context.update(self.get_metricas(self.filial))
        context.update(self.get_cycle_context())
        return context

    def get_title(self):
        return self.title or 'Dashboard'


# =====================================================================
# VIEW: DASHBOARD GERAL
# =====================================================================

class DashboardGeralView(BaseDashboardView):
    template_name = 'dashboard/dashboard_geral.html'
    permission_required = 'dashboard.view_dashboard_geral'
    dashboard_url_name = 'dashboard:dashboard_geral'

    def get_title(self):
        return f'Visão Geral — {self.filial}'

    def get_metricas(self, filial):
        return get_metricas_geral(filial)


# =====================================================================
# VIEW: DASHBOARD TREINAMENTOS
# =====================================================================

class DashboardTreinamentosView(BaseDashboardView):
    template_name = 'dashboard/dashboard_treinamentos.html'
    permission_required = 'dashboard.view_dashboard_treinamentos'
    dashboard_url_name = 'dashboard:dashboard_treinamentos'
    title = 'Dashboard Treinamentos'

    def get_metricas(self, filial):
        return get_metricas_treinamentos(filial, dias_alerta=15)


# =====================================================================
# VIEW: DASHBOARD TAREFAS
# =====================================================================

class DashboardTarefasView(BaseDashboardView):
    template_name = 'dashboard/dashboard_tarefas.html'
    permission_required = 'dashboard.view_dashboard_tarefas'
    dashboard_url_name = 'dashboard:dashboard_tarefas'
    title = 'Dashboard Tarefas'

    def get_metricas(self, filial):
        return get_metricas_tarefas(filial)


# =====================================================================
# VIEW: DASHBOARD EPI
# =====================================================================

class DashboardEpiView(BaseDashboardView):
    template_name = 'dashboard/dashboard_epi.html'
    permission_required = 'dashboard.view_dashboard_epi'
    dashboard_url_name = 'dashboard:dashboard_epi'
    title = 'Dashboard EPI'

    def get_metricas(self, filial):
        return get_metricas_epi(filial)


# =====================================================================
# VIEW: DASHBOARD DOCUMENTOS
# =====================================================================

class DashboardDocumentosView(BaseDashboardView):
    template_name = 'dashboard/dashboard_documentos.html'
    permission_required = 'dashboard.view_dashboard_documentos'
    dashboard_url_name = 'dashboard:dashboard_documentos'
    title = 'Dashboard Documentos'

    def get_metricas(self, filial):
        return get_metricas_documentos(filial, dias_alerta=30)


# =====================================================================
# VIEW: DASHBOARD PGR (comportamento especial)
# =====================================================================

class DashboardPgrView(BaseDashboardView):
    permission_required = 'dashboard.view_dashboard_pgr'
    dashboard_url_name = 'dashboard:dashboard_pgr'
    title = 'Dashboard PGR'

    def dispatch(self, request, *args, **kwargs):
        """PGR tem uma validação extra: o módulo precisa estar disponível."""
        if not pgr_disponivel():
            messages.error(request, "O módulo PGR não está disponível.")
            return render(request, 'dashboard/erro_configuracao.html', {
                'title': 'Erro de Configuração',
            })
        return super().dispatch(request, *args, **kwargs)

    def get_metricas(self, filial):
        return get_metricas_pgr(filial)

    def get_template_names(self):
        """PGR usa template fullscreen quando em modo carrossel."""
        is_cycling = self.request.GET.get('cycle') == 'true'
        if is_cycling:
            return ['dashboard/dashboard_pgr_fullscreen.html']
        return ['dashboard/dashboard_pgr.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hoje'] = timezone.now().date()
        return context

