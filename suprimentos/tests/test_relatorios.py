# suprimentos/tests/test_relatorios.py
import pytest
from decimal import Decimal
from datetime import date

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures locais. filial / material_factory / pedido_factory / usuario
# vêm do conftest.py.
# ---------------------------------------------------------------------------
@pytest.fixture
def contrato(db, filial):
    from suprimentos.models import Contrato
    return Contrato.objects.create(
        cm="CM-001",
        cliente="Cliente Teste",
        filial=filial,
        ativo=True,
    )


@pytest.fixture
def material_epi(material_factory):
    # tipo "EPI" -> chave de agrupamento; classificacao "EPI" -> verba EPI
    return material_factory(descricao="Capacete", tipo="EPI", classificacao="EPI")


@pytest.fixture
def material_eletrica(material_factory):
    return material_factory(descricao="Cabo", tipo="ELETRICA", classificacao="CONSUMO")


# ---------------------------------------------------------------------------
# Relatório por período
# ---------------------------------------------------------------------------
class TestRelatorioPorPeriodo:

    def test_soma_valores_dentro_do_periodo(self, contrato, material_epi, pedido_factory):
        pedido_factory(contrato, material_epi, date(2026, 1, 10), "100.00", qtd=2)
        pedido_factory(contrato, material_epi, date(2026, 1, 20), "50.00", qtd=1)

        from suprimentos.relatorios import total_periodo
        total = total_periodo(contrato=contrato, inicio=date(2026, 1, 1), fim=date(2026, 1, 31))
        assert total == Decimal("150.00")

    def test_ignora_pedidos_fora_do_periodo(self, contrato, material_epi, pedido_factory):
        pedido_factory(contrato, material_epi, date(2025, 12, 31), "999.00")
        pedido_factory(contrato, material_epi, date(2026, 1, 15), "100.00")

        from suprimentos.relatorios import total_periodo
        total = total_periodo(contrato=contrato, inicio=date(2026, 1, 1), fim=date(2026, 1, 31))
        assert total == Decimal("100.00")

    def test_periodo_vazio_retorna_zero(self, contrato, pedido_factory):
        from suprimentos.relatorios import total_periodo
        total = total_periodo(contrato=contrato, inicio=date(2026, 1, 1), fim=date(2026, 1, 31))
        assert total == Decimal("0.00")


# ---------------------------------------------------------------------------
# Agrupamento por tipo
# ---------------------------------------------------------------------------
class TestRelatorioPorTipo:

    def test_agrupa_por_tipo(self, contrato, material_epi, material_eletrica, pedido_factory):
        pedido_factory(contrato, material_epi, date(2026, 1, 10), "100.00")
        pedido_factory(contrato, material_eletrica, date(2026, 1, 10), "200.00")
        pedido_factory(contrato, material_eletrica, date(2026, 1, 12), "50.00")

        from suprimentos.relatorios import total_por_tipo
        resultado = total_por_tipo(contrato=contrato, inicio=date(2026, 1, 1), fim=date(2026, 1, 31))
        assert resultado["EPI"] == Decimal("100.00")
        assert resultado["ELETRICA"] == Decimal("250.00")

    def test_tipo_sem_movimento_nao_aparece(self, contrato, material_epi, pedido_factory):
        pedido_factory(contrato, material_epi, date(2026, 1, 10), "100.00")

        from suprimentos.relatorios import total_por_tipo
        resultado = total_por_tipo(contrato=contrato, inicio=date(2026, 1, 1), fim=date(2026, 1, 31))
        assert "ELETRICA" not in resultado


# ---------------------------------------------------------------------------
# Filtro por status
# ---------------------------------------------------------------------------
class TestRelatorioPorStatus:

    def test_considera_apenas_aprovados(self, contrato, material_epi, pedido_factory):
        pedido_factory(contrato, material_epi, date(2026, 1, 10), "100.00", status="APROVADO")
        pedido_factory(contrato, material_epi, date(2026, 1, 11), "999.00", status="CANCELADO")

        from suprimentos.relatorios import total_periodo
        total = total_periodo(contrato=contrato, inicio=date(2026, 1, 1), fim=date(2026, 1, 31))
        assert total == Decimal("100.00")




