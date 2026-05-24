#suprimentos/mixins.py
"""Mixins para aplicar permissões nas Views."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from . import permissions as perms


class _SuperuserBypassMixin(UserPassesTestMixin):
    """
    Base interna: superuser SEMPRE passa.
    UX amigável em caso de falha (não joga 403 cru).
    """
    raise_exception = False
    redirect_url_no_permission = 'suprimentos:dashboard'  # ajuste se quiser

    def _extra_test(self):
        """Subclasses sobrescrevem este método."""
        return False

    def test_func(self):
        u = self.request.user
        if not u.is_authenticated:
            return False
        if u.is_superuser:
            return True
        return self._extra_test()

    def handle_no_permission(self):
        # Não autenticado → manda pro login
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                settings.LOGIN_URL,
            )
        # Autenticado mas sem cargo → mensagem amigável
        messages.error(
            self.request,
            "Você não tem permissão para acessar esta área. "
            "Acesso restrito a cargos autorizados."
        )
        try:
            return redirect(self.redirect_url_no_permission)
        except Exception:
            return redirect('/')


class CoordenadorOuSuperiorMixin(_SuperuserBypassMixin):
    """Coordenador, Comprador, Gerente ou Superuser."""
    def _extra_test(self):
        u = self.request.user
        return (
            perms.is_coordenador(u)
            or perms.is_comprador(u)
            or perms.is_gerente(u)
        )


class SuprimentosOuSuperiorMixin(_SuperuserBypassMixin):
    """Bloqueia coordenador — usado em telas de Solicitação."""
    def _extra_test(self):
        return perms.pode_ver_solicitacao(self.request.user)


class GerenteApenasMixin(_SuperuserBypassMixin):
    """Apenas Gerente ou Superuser."""
    def _extra_test(self):
        return perms.is_gerente(self.request.user)
