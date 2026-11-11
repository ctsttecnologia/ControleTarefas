
# treinamentos/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.cache import cache
from django.http import HttpResponse
from core.mixins import ViewFilialScopedMixin, TecnicoScopeMixin
from core.utils import get_filial_ativa


class TreinamentoScopedMixin(LoginRequiredMixin, PermissionRequiredMixin,
                             ViewFilialScopedMixin, TecnicoScopeMixin):
    """Permissão + filial + escopo técnico em UMA linha."""
    tecnico_scope_lookup = 'participantes__funcionario'
    permission_view_all = 'treinamentos.ver_relatorios'


class FilialScopedMixin(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin):
    """Para models sem escopo técnico (TipoCurso, CursoEAD)."""


def filial_do_request(request):
    return get_filial_ativa(request.user, request)


class RateLimitPublicMixin:
    RATE_LIMIT_MAX, RATE_LIMIT_WINDOW = 30, 60

    def dispatch(self, request, *args, **kwargs):
        ip = request.META.get('REMOTE_ADDR', 'unknown')  # proxy confiável deve setar REMOTE_ADDR
        key = f'rl:treinamentos:{self.__class__.__name__}:{ip}'
        if cache.get_or_set(key, 0, self.RATE_LIMIT_WINDOW) >= self.RATE_LIMIT_MAX:
            return HttpResponse('Muitas requisições. Tente novamente em 1 minuto.', status=429)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, self.RATE_LIMIT_WINDOW)
        return super().dispatch(request, *args, **kwargs)

class PaginacaoQSMixin:
    """Mantém os filtros na paginação e gera a faixa de páginas com reticências."""
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.request.GET.copy()
        qs.pop('page', None)
        ctx['qs'] = qs.urlencode()
        if page := ctx.get('page_obj'):
            ctx['paginas'] = page.paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1)
        return ctx

class FiltrosPaginacaoMixin:
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.request.GET.copy()
        qs.pop("page", None)
        ctx["filtros_qs"] = qs.urlencode()
        page = ctx.get("page_obj")
        ctx["total_registros"] = page.paginator.count if page else len(ctx["object_list"])
        return ctx
