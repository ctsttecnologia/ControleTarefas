
# suprimentos/tests/test_mixins.py
"""Testes para os mixins de permissão do app suprimentos."""
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from suprimentos.mixins import (
    _SuperuserBypassMixin,
    CoordenadorOuSuperiorMixin,
    SuprimentosOuSuperiorMixin,
    GerenteApenasMixin,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_view(mixin_cls, user, path='/suprimentos/teste/'):
    """Instancia um mixin com um request fake já configurado."""
    request = RequestFactory().get(path)
    request.user = user
    view = mixin_cls()
    view.request = request
    return view


def fake_user(authenticated=True, superuser=False):
    u = MagicMock()
    u.is_authenticated = authenticated
    u.is_superuser = superuser
    return u


# ===========================================================================
# == _SuperuserBypassMixin (base) — test_func
# ===========================================================================
class TestSuperuserBypassTestFunc:

    def test_nao_autenticado_retorna_false(self):
        view = make_view(_SuperuserBypassMixin, AnonymousUser())
        assert view.test_func() is False

    def test_superuser_retorna_true(self):
        view = make_view(_SuperuserBypassMixin, fake_user(superuser=True))
        assert view.test_func() is True

    def test_autenticado_comum_chama_extra_test(self):
        # _extra_test padrão da base retorna False
        view = make_view(_SuperuserBypassMixin, fake_user())
        assert view.test_func() is False

    def test_extra_test_padrao_retorna_false(self):
        view = make_view(_SuperuserBypassMixin, fake_user())
        assert view._extra_test() is False


# ===========================================================================
# == _SuperuserBypassMixin — handle_no_permission
# ===========================================================================
class TestSuperuserBypassHandleNoPermission:

    def test_nao_autenticado_redireciona_login(self):
        view = make_view(_SuperuserBypassMixin, AnonymousUser())
        with patch('suprimentos.mixins.redirect_to_login') as mock_login:
            mock_login.return_value = 'LOGIN_REDIRECT'
            result = view.handle_no_permission()
        assert result == 'LOGIN_REDIRECT'
        mock_login.assert_called_once()

    def test_autenticado_sem_permissao_redireciona_com_mensagem(self):
        view = make_view(_SuperuserBypassMixin, fake_user())
        with patch('suprimentos.mixins.messages.error') as mock_msg, \
             patch('suprimentos.mixins.redirect') as mock_redirect:
            mock_redirect.return_value = 'DASHBOARD_REDIRECT'
            result = view.handle_no_permission()
        assert result == 'DASHBOARD_REDIRECT'
        mock_msg.assert_called_once()
        mock_redirect.assert_called_once_with('suprimentos:dashboard')

    def test_redirect_falha_cai_no_fallback_raiz(self):
        """Cobre o except → redirect('/')."""
        view = make_view(_SuperuserBypassMixin, fake_user())
        with patch('suprimentos.mixins.messages.error'), \
             patch('suprimentos.mixins.redirect') as mock_redirect:
            # 1ª chamada (dashboard) levanta; 2ª chamada ('/') retorna
            mock_redirect.side_effect = [Exception('no reverse'), 'ROOT_REDIRECT']
            result = view.handle_no_permission()
        assert result == 'ROOT_REDIRECT'
        assert mock_redirect.call_count == 2
        mock_redirect.assert_any_call('suprimentos:dashboard')
        mock_redirect.assert_any_call('/')


# ===========================================================================
# == CoordenadorOuSuperiorMixin._extra_test
# ===========================================================================
class TestCoordenadorOuSuperiorMixin:

    def test_coordenador_passa(self):
        view = make_view(CoordenadorOuSuperiorMixin, fake_user())
        with patch('suprimentos.mixins.perms.is_coordenador', return_value=True), \
             patch('suprimentos.mixins.perms.is_suprimentos', return_value=False), \
             patch('suprimentos.mixins.perms.is_gerente', return_value=False):
            assert view._extra_test() is True

    def test_suprimentos_passa(self):
        view = make_view(CoordenadorOuSuperiorMixin, fake_user())
        with patch('suprimentos.mixins.perms.is_coordenador', return_value=False), \
             patch('suprimentos.mixins.perms.is_suprimentos', return_value=True), \
             patch('suprimentos.mixins.perms.is_gerente', return_value=False):
            assert view._extra_test() is True

    def test_gerente_passa(self):
        view = make_view(CoordenadorOuSuperiorMixin, fake_user())
        with patch('suprimentos.mixins.perms.is_coordenador', return_value=False), \
             patch('suprimentos.mixins.perms.is_suprimentos', return_value=False), \
             patch('suprimentos.mixins.perms.is_gerente', return_value=True):
            assert view._extra_test() is True

    def test_nenhum_cargo_falha(self):
        view = make_view(CoordenadorOuSuperiorMixin, fake_user())
        with patch('suprimentos.mixins.perms.is_coordenador', return_value=False), \
             patch('suprimentos.mixins.perms.is_suprimentos', return_value=False), \
             patch('suprimentos.mixins.perms.is_gerente', return_value=False):
            assert view._extra_test() is False


# ===========================================================================
# == SuprimentosOuSuperiorMixin._extra_test
# ===========================================================================
class TestSuprimentosOuSuperiorMixin:

    def test_pode_ver_solicitacao_true(self):
        view = make_view(SuprimentosOuSuperiorMixin, fake_user())
        with patch('suprimentos.mixins.perms.pode_ver_solicitacao', return_value=True):
            assert view._extra_test() is True

    def test_pode_ver_solicitacao_false(self):
        view = make_view(SuprimentosOuSuperiorMixin, fake_user())
        with patch('suprimentos.mixins.perms.pode_ver_solicitacao', return_value=False):
            assert view._extra_test() is False


# ===========================================================================
# == GerenteApenasMixin._extra_test
# ===========================================================================
class TestGerenteApenasMixin:

    def test_gerente_true(self):
        view = make_view(GerenteApenasMixin, fake_user())
        with patch('suprimentos.mixins.perms.is_gerente', return_value=True):
            assert view._extra_test() is True

    def test_nao_gerente_false(self):
        view = make_view(GerenteApenasMixin, fake_user())
        with patch('suprimentos.mixins.perms.is_gerente', return_value=False):
            assert view._extra_test() is False

