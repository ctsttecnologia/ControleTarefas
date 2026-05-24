
from unittest.mock import MagicMock

import pytest

from core.constants import SESSION_FILIAL_ATIVA
from core.utils import get_filial_ativa


@pytest.mark.django_db
def test_get_filial_ativa_via_sessao(usuario_factory, filial_factory):
    user = usuario_factory()
    filial = filial_factory()
    filial.usuarios.add(user)  # ajuste conforme seu modelo

    request = MagicMock()
    request.session = {SESSION_FILIAL_ATIVA: filial.pk}

    assert get_filial_ativa(user, request) == filial


@pytest.mark.django_db
def test_get_filial_ativa_fallback_filial_padrao(usuario_factory, filial_factory):
    user = usuario_factory()
    filial = filial_factory()
    user.filial_padrao = filial
    user.save()

    request = MagicMock()
    request.session = {}

    assert get_filial_ativa(user, request) == filial


def test_get_filial_ativa_anonimo():
    user = MagicMock(is_authenticated=False)
    assert get_filial_ativa(user, None) is None

