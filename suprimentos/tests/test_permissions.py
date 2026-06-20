
# suprimentos/tests/test_permissions.py
"""Testes das funções de permissão de suprimentos (100% sem DB)."""
from django.contrib.auth.models import Group
from unittest.mock import MagicMock

import pytest

from core.constants import GRUPO_GERENTE
from suprimentos.permissions import (
    _in_group,
    is_gerencia,
    is_comprador,
    is_coordenador,
)

def _user(authenticated=True, superuser=False, groups=None):
    """Cria um user fake com .groups.filter(...).exists() controlável."""
    user = MagicMock()
    user.is_authenticated = authenticated
    user.is_superuser = superuser

    grupos = set(groups or [])

    def _filter(name__in=None):
        qs = MagicMock()
        qs.exists.return_value = bool(grupos & set(name__in or []))
        return qs

    user.groups.filter.side_effect = _filter
    return user


# ═══════════════════════════════════════════════
# _in_group
# ═══════════════════════════════════════════════
class TestInGroup:

    def test_nao_autenticado_retorna_false(self):
        user = _user(authenticated=False)
        assert _in_group(user, "Qualquer") is False
        user.groups.filter.assert_not_called()

    def test_superuser_retorna_true(self):
        user = _user(superuser=True)
        assert _in_group(user, "Qualquer") is True
        user.groups.filter.assert_not_called()

    def test_pertence_ao_grupo(self):
        user = _user(groups=["Comprador"])
        assert _in_group(user, "Comprador", "Suprimentos") is True

    def test_nao_pertence_ao_grupo(self):
        user = _user(groups=["Outro"])
        assert _in_group(user, "Comprador", "Suprimentos") is False


# ═══════════════════════════════════════════════
# is_gerencia
# ═══════════════════════════════════════════════
class TestIsGerencia:

    @pytest.mark.parametrize("grupo", ["Gerência", "Gerencia", "Admin"])
    def test_grupos_validos(self, grupo):
        assert is_gerencia(_user(groups=[grupo])) is True

    def test_grupo_invalido(self):
        assert is_gerencia(_user(groups=["Comprador"])) is False

    def test_superuser(self):
        assert is_gerencia(_user(superuser=True)) is True

    def test_nao_autenticado(self):
        assert is_gerencia(_user(authenticated=False)) is False

    def test_is_gerente_true_quando_no_grupo(self, usuario):
        grupo = Group.objects.create(name=GRUPO_GERENTE)
        usuario.groups.add(grupo)
        usuario.refresh_from_db()
        assert usuario.is_gerente is True

# ═══════════════════════════════════════════════
# is_comprador
# ═══════════════════════════════════════════════
class TestIsComprador:

    @pytest.mark.parametrize("grupo", ["Comprador", "Suprimentos"])
    def test_grupos_validos(self, grupo):
        assert is_comprador(_user(groups=[grupo])) is True

    def test_grupo_invalido(self):
        assert is_comprador(_user(groups=["Gerência"])) is False


# ═══════════════════════════════════════════════
# is_coordenador
# ═══════════════════════════════════════════════
class TestIsCoordenador:

    @pytest.mark.parametrize("grupo", ["Coordenador", "Solicitante"])
    def test_grupos_validos(self, grupo):
        assert is_coordenador(_user(groups=[grupo])) is True

    def test_grupo_invalido(self):
        assert is_coordenador(_user(groups=["Admin"])) is False


is_suprimentos = is_comprador
is_gerente = is_gerencia

def pode_ver_solicitacao(user):
    """Suprimentos ou Gerência (bloqueia coordenador puro)."""
    return is_comprador(user) or is_gerencia(user)

# pytest suprimentos/tests/test_permissions.py --cov=suprimentos.permissions --cov-report=term-missing -v

