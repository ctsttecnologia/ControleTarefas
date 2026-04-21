
# usuario/tests/test_template_utils.py
"""Testes do template filter `get_item`."""

from usuario.templatetags.template_utils import get_item


class TestGetItemFilter:
    """Filtro que acessa chaves de dicionário dentro de templates."""

    def test_retorna_valor_quando_chave_existe(self):
        dicionario = {'nome': 'Emerson', 'idade': 30}
        assert get_item(dicionario, 'nome') == 'Emerson'
        assert get_item(dicionario, 'idade') == 30

    def test_retorna_none_quando_chave_nao_existe(self):
        assert get_item({'a': 1}, 'inexistente') is None

    def test_funciona_com_dicionario_vazio(self):
        assert get_item({}, 'qualquer') is None

    def test_aceita_valor_none_como_valor(self):
        assert get_item({'campo': None}, 'campo') is None
