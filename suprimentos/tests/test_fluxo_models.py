
# suprimentos/tests/test_fluxo_models.py
"""
Testes de regra de negócio dos models (sem passar pelas views).
Garante que o pipeline funciona independente da camada HTTP.
"""
import pytest
from decimal import Decimal
from datetime import date
from datetime import datetime
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_gerar_solicitacao_a_partir_de_pedido_aprovado(
    contrato_com_verba, material, usuario, pedido_factory
):
    from suprimentos.models import Pedido, ItemSolicitacao

    pedido = pedido_factory(
        contrato=contrato_com_verba, material=material,
        data=date.today(), valor="150.00", qtd=3, status="APROVADO",
    )
    pedido.aprovador = usuario
    pedido.data_aprovacao = date.today()
    pedido.save(update_fields=["aprovador", "data_aprovacao"])

    sol = pedido.gerar_solicitacao_compra(usuario=usuario)

    pedido.refresh_from_db()
    assert pedido.status == Pedido.StatusChoices.SOLICITACAO_GERADA
    assert pedido.solicitacao_gerada_id == sol.pk
    assert sol.itens.count() == 1
    item = sol.itens.first()
    assert item.status == ItemSolicitacao.StatusItem.PENDENTE_COTACAO
    assert item.quantidade == Decimal("3")


def test_nao_gera_solicitacao_se_pedido_nao_aprovado(
    contrato_com_verba, material, usuario, pedido_factory
):
    from django.core.exceptions import ValidationError

    pedido = pedido_factory(
        contrato=contrato_com_verba, material=material,
        data=date.today(), valor="100.00", status="PENDENTE",
    )
    with pytest.raises(ValidationError):
        pedido.gerar_solicitacao_compra(usuario=usuario)


def test_nao_gera_solicitacao_duplicada(
    contrato_com_verba, material, usuario, pedido_factory
):
    from django.core.exceptions import ValidationError

    pedido = pedido_factory(
        contrato=contrato_com_verba, material=material,
        data=date.today(), valor="100.00", status="APROVADO",
    )
    pedido.gerar_solicitacao_compra(usuario=usuario)
    with pytest.raises(ValidationError):
        pedido.gerar_solicitacao_compra(usuario=usuario)


def test_menor_cotacao_e_valor_total(
    solicitacao, fornecedor, usuario, cotacao_factory
):
    """A menor cotação deve ser a de menor valor_unitario."""
    from suprimentos.models import Parceiro

    item = solicitacao.itens.first()
    forn2 = Parceiro.objects.create(
        nome_fantasia="Forn2", razao_social="Forn2 LTDA",
        cnpj="22.222.222/0001-22", eh_fornecedor=True, ativo=True,
        filial=solicitacao.filial,
    )

    c1 = cotacao_factory(item, valor_unitario="100.00")
    c2 = cotacao_factory(item, valor_unitario="60.00", fornecedor_obj=forn2)

    assert item.menor_cotacao.pk == c2.pk
    assert c2.is_menor_preco is True
    assert c1.is_menor_preco is False
    # item criado com qtd=2 na fixture `solicitacao`
    assert c2.valor_total == Decimal("120.00")


def test_constraint_cotacao_unica_por_fornecedor(
    solicitacao, cotacao_factory
):
    from django.db import IntegrityError

    item = solicitacao.itens.first()
    cotacao_factory(item, valor_unitario="50.00")
    with pytest.raises(IntegrityError):
        cotacao_factory(item, valor_unitario="40.00")  # mesmo fornecedor


def test_pedido_compra_recalcula_total_ao_adicionar_item(contexto_fluxo):
    pc = contexto_fluxo["pedido_compra"]
    pc.refresh_from_db()
    # item criado com qtd=2 e unitário 45.00
    assert pc.valor_total == Decimal("90.00")   # ✅ 45.00 × 2


def test_atualizar_status_entrega_parcial_e_total(contexto_fluxo):
    from suprimentos.models import PedidoCompra

    pc = contexto_fluxo["pedido_compra"]
    item = pc.itens.first()

    # Recebimento parcial
    item.quantidade_recebida = Decimal("1")
    item.save(update_fields=["quantidade_recebida"])
    pc.atualizar_status_entrega()
    pc.refresh_from_db()
    assert pc.status == PedidoCompra.StatusPC.ENTREGA_PARCIAL

    # Recebimento total
    item.quantidade_recebida = item.quantidade
    item.save(update_fields=["quantidade_recebida"])
    pc.atualizar_status_entrega()
    pc.refresh_from_db()
    assert pc.status == PedidoCompra.StatusPC.ENTREGUE
    assert pc.data_entrega_efetiva is not None

