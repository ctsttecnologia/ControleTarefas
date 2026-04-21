
# usuario/tests/test_context_processors.py
"""
Testes do context processor `usuario_filial_context`.

Cobre os três caminhos da função:
    1. Usuário anônimo         -> retorna {}
    2. Autenticado c/ filial   -> retorna dict populado
    3. Autenticado s/ filial   -> retorna dict com None
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from usuario.context_processors import usuario_filial_context


@pytest.mark.django_db
class TestUsuarioFilialContext:
    """Testa o context processor que injeta filial_ativa nos templates."""

    def test_usuario_anonimo_retorna_dict_vazio(self):
        """Usuário não autenticado NÃO deve receber dados de filial."""
        request = RequestFactory().get('/')
        request.user = AnonymousUser()

        context = usuario_filial_context(request)

        assert context == {}

    def test_usuario_autenticado_com_filial_ativa(self, gerente, filial_a):
        """Usuário logado recebe filial_ativa_global e filiais_permitidas_global."""
        gerente.filial_ativa = filial_a
        gerente.filiais_permitidas.add(filial_a)
        gerente.save()

        request = RequestFactory().get('/')
        request.user = gerente

        context = usuario_filial_context(request)

        assert 'filial_ativa_global' in context
        assert 'filiais_permitidas_global' in context
        assert context['filial_ativa_global'] == filial_a
        assert filial_a in context['filiais_permitidas_global']

    def test_usuario_autenticado_sem_filial_ativa(self, usuario_comum):
        """Se `filial_ativa` é None, o processor não quebra e retorna None."""
        usuario_comum.filial_ativa = None
        usuario_comum.save()

        request = RequestFactory().get('/')
        request.user = usuario_comum

        context = usuario_filial_context(request)

        assert context['filial_ativa_global'] is None
        assert 'filiais_permitidas_global' in context

# pytest usuario/tests/test_context_processors.py -v --cov=usuario.context_processors --cov-report=term-missing
