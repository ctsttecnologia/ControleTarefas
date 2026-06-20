
from email.headerregistry import Group
from unittest.mock import MagicMock
import pytest
from suprimentos.permissions import is_gerente
from usuario.models import Usuario
from core.constants import SESSION_FILIAL_ATIVA
from core.utils import get_filial_ativa


@pytest.mark.django_db
def test_get_filial_ativa_fallback_filial_padrao(usuario_factory, filial_a, filial_b):
    user = usuario_factory()
    user.filial_ativa = filial_a       # campo lido pelo fallback de get_filial_ativa()
    user.save()

    request = MagicMock()
    request.session = {}

    assert get_filial_ativa(user, request) == filial_a

def test_get_filial_ativa_anonimo():
    user = MagicMock(is_authenticated=False)
    assert get_filial_ativa(user, None) is None

