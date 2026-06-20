
# suprimentos/tests/test_serializers.py
"""
Testes dos serializers de suprimentos.

Foco em cobrir 100% das linhas faltantes:
- Campos derivados (source='...', SerializerMethodField)
- Ramos None vs preenchido (aprovador_nome, recebedor_nome)
- Conversão de totais_por_classificacao (Decimal -> str)
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from suprimentos.serializers import (
    ParceiroSerializer, ParceiroResumoSerializer,
    MaterialSerializer,
    ContratoSerializer, ContratoResumoSerializer,
    VerbaContratoSerializer,
    ItemPedidoSerializer,
    PedidoListSerializer, PedidoDetailSerializer,
)


# ═══════════════════════════════════════════════
# Helpers — objetos "fake" leves (sem tocar o banco)
# ═══════════════════════════════════════════════
def _fake(**attrs):
    """Cria um objeto simples com os atributos passados."""
    obj = MagicMock()
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


# ═══════════════════════════════════════════════
# PARCEIRO
# ═══════════════════════════════════════════════
class TestParceiroSerializer:

    def test_campos_declarados(self):
        s = ParceiroSerializer()
        assert 'filial_nome' in s.fields
        assert 'razao_social' in s.fields
        assert s.fields['id'].read_only

    def test_filial_nome_source(self):
        """filial_nome deve apontar para filial.nome."""
        s = ParceiroSerializer()
        assert s.fields['filial_nome'].source == 'filial.nome'
        assert s.fields['filial_nome'].read_only


class TestParceiroResumoSerializer:

    def test_fields_compactos(self):
        s = ParceiroResumoSerializer()
        assert set(s.fields) == {
            'id', 'nome_fantasia', 'cnpj', 'eh_fabricante', 'eh_fornecedor',
        }


# ═══════════════════════════════════════════════
# MATERIAL
# ═══════════════════════════════════════════════
class TestMaterialSerializer:

    def test_displays_e_sources(self):
        s = MaterialSerializer()
        assert s.fields['classificacao_display'].source == 'get_classificacao_display'
        assert s.fields['tipo_display'].source == 'get_tipo_display'
        assert s.fields['unidade_display'].source == 'get_unidade_display'
        assert s.fields['ncm_codigo'].source == 'ncm.codigo'
        assert s.fields['grupo_tributario_nome'].source == 'grupo_tributario.nome'

    def test_defaults_none(self):
        """ncm_codigo e grupo_tributario_nome têm default=None."""
        s = MaterialSerializer()
        assert s.fields['ncm_codigo'].default is None
        assert s.fields['grupo_tributario_nome'].default is None

    def test_read_only_fields(self):
        s = MaterialSerializer()
        assert s.fields['id'].read_only
        assert s.fields['codigo'].read_only


# ═══════════════════════════════════════════════
# CONTRATO
# ═══════════════════════════════════════════════
class TestContratoSerializer:

    def test_filial_nome(self):
        s = ContratoSerializer()
        assert s.fields['filial_nome'].source == 'filial.nome'

    def test_resumo_fields(self):
        s = ContratoResumoSerializer()
        assert set(s.fields) == {'id', 'cm', 'cliente'}


# ═══════════════════════════════════════════════
# VERBA CONTRATO
# ═══════════════════════════════════════════════
class TestVerbaContratoSerializer:

    def test_campos_decimais_read_only(self):
        s = VerbaContratoSerializer()
        for campo in [
            'verba_total', 'compra_epi', 'compra_consumo', 'compra_ferramenta',
            'compra_total', 'saldo_epi', 'saldo_consumo', 'saldo_ferramenta',
            'saldo_total',
        ]:
            assert s.fields[campo].read_only, f'{campo} deveria ser read_only'

    def test_contrato_cm_source(self):
        s = VerbaContratoSerializer()
        assert s.fields['contrato_cm'].source == 'contrato.cm'

    def test_serializa_objeto(self):
        """Serializa um objeto fake com todos os campos calculados."""
        verba = _fake(
            id=1, ano=2026, mes=6,
            verba_epi=Decimal('100'), verba_consumo=Decimal('200'),
            verba_ferramenta=Decimal('300'), verba_total=Decimal('600'),
            compra_epi=Decimal('10'), compra_consumo=Decimal('20'),
            compra_ferramenta=Decimal('30'), compra_total=Decimal('60'),
            saldo_epi=Decimal('90'), saldo_consumo=Decimal('180'),
            saldo_ferramenta=Decimal('270'), saldo_total=Decimal('540'),
        )
        verba.contrato.cm = 'CM-001'
        verba.contrato_id = 5
        data = VerbaContratoSerializer(verba).data
        assert data['contrato_cm'] == 'CM-001'
        assert data['verba_total'] == '600.00'
        assert data['saldo_total'] == '540.00'


# ═══════════════════════════════════════════════
# ITEM PEDIDO
# ═══════════════════════════════════════════════
class TestItemPedidoSerializer:

    def test_sources_material(self):
        s = ItemPedidoSerializer()
        assert s.fields['material_descricao'].source == 'material.descricao'
        assert s.fields['material_classificacao'].source == 'material.classificacao'
        assert s.fields['material_unidade'].source == 'material.get_unidade_display'

    def test_read_only_fields(self):
        s = ItemPedidoSerializer()
        for campo in ['id', 'valor_total', 'custo_real', 'total_creditos', 'total_impostos']:
            assert s.fields[campo].read_only


# ═══════════════════════════════════════════════
# PEDIDO LIST
# ═══════════════════════════════════════════════
class TestPedidoListSerializer:

    def test_sources(self):
        s = PedidoListSerializer()
        assert s.fields['contrato_cm'].source == 'contrato.cm'
        assert s.fields['contrato_cliente'].source == 'contrato.cliente'
        assert s.fields['solicitante_nome'].source == 'solicitante.get_full_name'
        assert s.fields['status_display'].source == 'get_status_display'


# ═══════════════════════════════════════════════
# PEDIDO DETAIL — foco nos SerializerMethodField
# ═══════════════════════════════════════════════
class TestPedidoDetailSerializer:

    def test_aprovador_nome_preenchido(self):
        """Ramo: aprovador existe -> retorna get_full_name()."""
        pedido = _fake()
        pedido.aprovador = _fake()
        pedido.aprovador.get_full_name.return_value = 'João Aprovador'
        s = PedidoDetailSerializer()
        assert s.get_aprovador_nome(pedido) == 'João Aprovador'

    def test_aprovador_nome_none(self):
        """Ramo: sem aprovador -> None."""
        pedido = _fake(aprovador=None)
        s = PedidoDetailSerializer()
        assert s.get_aprovador_nome(pedido) is None

    def test_recebedor_nome_preenchido(self):
        pedido = _fake()
        pedido.recebedor = _fake()
        pedido.recebedor.get_full_name.return_value = 'Maria Recebedora'
        s = PedidoDetailSerializer()
        assert s.get_recebedor_nome(pedido) == 'Maria Recebedora'

    def test_recebedor_nome_none(self):
        pedido = _fake(recebedor=None)
        s = PedidoDetailSerializer()
        assert s.get_recebedor_nome(pedido) is None

    def test_totais_por_classificacao_converte_decimal(self):
        """Decimais devem virar str no dict de retorno."""
        pedido = _fake()
        pedido.totais_por_classificacao.return_value = {
            'EPI': Decimal('100.50'),
            'CONSUMO': Decimal('0'),
        }
        s = PedidoDetailSerializer()
        result = s.get_totais_por_classificacao(pedido)
        assert result == {'EPI': '100.50', 'CONSUMO': '0'}
        assert all(isinstance(v, str) for v in result.values())

    def test_totais_vazio(self):
        """Dict vazio -> dict vazio."""
        pedido = _fake()
        pedido.totais_por_classificacao.return_value = {}
        s = PedidoDetailSerializer()
        assert s.get_totais_por_classificacao(pedido) == {}


# pytest suprimentos/tests/test_serializers.py --cov=suprimentos.serializers --cov-report=term-missing -v
