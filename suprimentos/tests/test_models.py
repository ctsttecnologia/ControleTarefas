
# suprimentos/tests/test_models.py
"""
Testes de model do app Suprimentos.

Cobrem:
  - GeraÃ§Ã£o automÃ¡tica de cÃ³digo (Material) e nÃºmero (Pedido, SolicitaÃ§Ã£o, PC)
  - Properties calculadas (valor_total, saldos de verba, tributaÃ§Ã£o sem grupo)
  - Workflow Pedido â†’ SolicitacaoCompra
  - CotaÃ§Ã£o (valor_total, menor preÃ§o, unique constraint)
  - PedidoCompra (recalcular_total, atualizar_status_entrega, saldos)
  - EstoqueConsumo (saldo_material)
"""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from suprimentos.models import (
    CategoriaMaterial,
    TipoMaterial,
    UnidadeMedida,
    Parceiro,
    Material,
    Contrato,
    VerbaContrato,
    Pedido,
    HistoricoPedido,
    ItemPedido,
    SolicitacaoCompra,
    ItemSolicitacao,
    Cotacao,
    PedidoCompra,
    ItemPedidoCompra,
    EstoqueConsumo,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def material(db):
    return Material.objects.create(
        descricao="Cimento CP-II 50kg",
        classificacao=CategoriaMaterial.CONSUMO,
        tipo=TipoMaterial.CIVIL,
        unidade=UnidadeMedida.UNID,
        valor_unitario=Decimal("35.00"),
    )


@pytest.fixture
def material_epi(db):
    return Material.objects.create(
        descricao="Luva NitrÃ­lica",
        classificacao=CategoriaMaterial.EPI,
        tipo=TipoMaterial.EPI,
        unidade=UnidadeMedida.PAR,
        valor_unitario=Decimal("12.50"),
    )


@pytest.fixture
def contrato(db, filial):
    return Contrato.objects.create(
        cm="CM-001", cliente="Cliente Teste", filial=filial,
    )


@pytest.fixture
def fornecedor(db, filial):
    return Parceiro.objects.create(
        nome_fantasia="Fornecedor A",
        eh_fornecedor=True,
        ativo=True,
        filial=filial,
    )


@pytest.fixture
def fornecedor_b(db, filial):
    return Parceiro.objects.create(
        nome_fantasia="Fornecedor B",
        eh_fornecedor=True,
        ativo=True,
        filial=filial,
    )


@pytest.fixture
def pedido(db, contrato, filial, usuario):
    return Pedido.objects.create(
        contrato=contrato,
        filial=filial,
        solicitante=usuario,
        tipo_obra="CM",
    )


class TestMaterial:
    def test_codigo_gerado_automaticamente(self, material):
        assert material.codigo.startswith("CON-")
        assert len(material.codigo) == len("CON-") + 6

    def test_codigo_respeita_classificacao(self, material_epi):
        assert material_epi.codigo.startswith("EPI-")

    def test_codigo_manual_nao_sobrescrito(self, db):
        m = Material.objects.create(
            codigo="MEU-COD",
            descricao="Item manual",
            classificacao=CategoriaMaterial.CONSUMO,
            tipo=TipoMaterial.CIVIL,
        )
        assert m.codigo == "MEU-COD"

    def test_str(self, material):
        assert "Cimento CP-II 50kg" in str(material)

    def test_str_com_marca(self, db):
        m = Material.objects.create(
            descricao="Tinta", classificacao=CategoriaMaterial.CONSUMO,
            tipo=TipoMaterial.CIVIL, marca="Coral",
        )
        assert "(Coral)" in str(m)

    def test_calcular_custo_compra_sem_grupo(self, material):
        calc = material.calcular_custo_compra(Decimal("100.00"), 2)
        assert calc["sem_grupo"] is True
        assert calc["valor_produtos"] == Decimal("100.00")
        assert calc["custo_real"] == Decimal("100.00")
        assert calc["custo_unitario"] == Decimal("50.00")

    def test_tem_vinculo_estoque_consumo(self, material):
        # CONSUMO sempre considerado True
        assert material.tem_vinculo_estoque is True

    def test_tem_vinculo_estoque_epi_sem_equipamento(self, material_epi):
        assert material_epi.tem_vinculo_estoque is False

    def test_info_tributaria_sem_grupo(self, material):
        assert material.info_tributaria_unitaria == {"sem_grupo": True}


    def test_str(self, contrato):
        assert str(contrato) == "CM CM-001 - Cliente Teste"

    def test_verba_do_mes_cria_se_nao_existe(self, contrato):
        verba = contrato.verba_do_mes(2026, 6)
        assert isinstance(verba, VerbaContrato)
        assert verba.ano == 2026
        assert verba.mes == 6

    def test_verba_do_mes_idempotente(self, contrato):
        v1 = contrato.verba_do_mes(2026, 6)
        v2 = contrato.verba_do_mes(2026, 6)
        assert v1.pk == v2.pk

    def test_verba_total(self, contrato):
        verba = contrato.verba_do_mes(2026, 6)
        verba.verba_epi = Decimal("100.00")
        verba.verba_consumo = Decimal("200.00")
        verba.verba_ferramenta = Decimal("50.00")
        verba.save()
        assert verba.verba_total == Decimal("350.00")

    def test_saldo_sem_compras(self, contrato):
        verba = contrato.verba_do_mes(2026, 6)
        verba.verba_consumo = Decimal("500.00")
        verba.save()
        assert verba.saldo_consumo == Decimal("500.00")
        assert verba.compra_consumo == Decimal("0.00")

    def test_str_verba(self, contrato):
        verba = contrato.verba_do_mes(2026, 6)
        assert str(verba) == "CM-001 \u2014 06/2026"  # \u2014 = travessão (—)


class TestPedido:
    def test_numero_gerado(self, pedido):
        prefixo = f"PED-{timezone.now().strftime('%Y%m')}-"
        assert pedido.numero.startswith(prefixo)

    def test_numero_sequencial(self, contrato, filial, usuario):
        p1 = Pedido.objects.create(
            contrato=contrato, filial=filial,
            solicitante=usuario, tipo_obra="CM",
        )
        p2 = Pedido.objects.create(
            contrato=contrato, filial=filial,
            solicitante=usuario, tipo_obra="CM",
        )
        assert p1.numero != p2.numero

    def test_status_inicial_rascunho(self, pedido):
        assert pedido.status == Pedido.StatusChoices.RASCUNHO

    def test_valor_total_sem_itens(self, pedido):
        assert pedido.valor_total == Decimal("0.00")

    def test_valor_total_com_itens(self, pedido, material):
        ItemPedido.objects.create(
            pedido=pedido, material=material,
            quantidade=3, valor_unitario=Decimal("10.00"),
        )
        assert pedido.valor_total == Decimal("30.00")

    def test_totais_por_classificacao(self, pedido, material, material_epi):
        ItemPedido.objects.create(
            pedido=pedido, material=material,
            quantidade=2, valor_unitario=Decimal("10.00"),
        )
        ItemPedido.objects.create(
            pedido=pedido, material=material_epi,
            quantidade=1, valor_unitario=Decimal("5.00"),
        )
        totais = pedido.totais_por_classificacao()
        assert totais[CategoriaMaterial.CONSUMO] == Decimal("20.00")
        assert totais[CategoriaMaterial.EPI] == Decimal("5.00")

    def test_str(self, pedido):
        assert pedido.numero in str(pedido)

    def test_historico_registrar_incrementa_versao(self, pedido, usuario):
        h1 = HistoricoPedido.registrar(
            pedido=pedido, descricao="Criado", responsavel=usuario,
        )
        h2 = HistoricoPedido.registrar(
            pedido=pedido, descricao="Editado", responsavel=usuario,
        )
        assert h1.versao == 1
        assert h2.versao == 2


class TestItemPedido:
    def test_valor_total_calculado_no_save(self, pedido, material):
        item = ItemPedido.objects.create(
            pedido=pedido, material=material,
            quantidade=4, valor_unitario=Decimal("25.00"),
        )
        assert item.valor_total == Decimal("100.00")

    def test_str(self, pedido, material):
        item = ItemPedido.objects.create(
            pedido=pedido, material=material,
            quantidade=2, valor_unitario=Decimal("10.00"),
        )
        assert str(item) == "2x Cimento CP-II 50kg"


class TestGerarSolicitacaoCompra:
    def _pedido_aprovado_com_item(self, pedido, material, usuario):
        ItemPedido.objects.create(
            pedido=pedido, material=material,
            quantidade=2, valor_unitario=Decimal("10.00"),
        )
        pedido.status = Pedido.StatusChoices.APROVADO
        pedido.aprovador = usuario
        pedido.data_aprovacao = timezone.now()
        pedido.save()
        return pedido

    def test_gera_solicitacao_quando_aprovado(self, pedido, material, usuario):
        self._pedido_aprovado_com_item(pedido, material, usuario)
        sol = pedido.gerar_solicitacao_compra(usuario)
        assert isinstance(sol, SolicitacaoCompra)
        assert pedido.status == Pedido.StatusChoices.SOLICITACAO_GERADA
        assert pedido.solicitacao_gerada_id == sol.pk

    def test_gera_itens_solicitacao(self, pedido, material, usuario):
        self._pedido_aprovado_com_item(pedido, material, usuario)
        sol = pedido.gerar_solicitacao_compra(usuario)
        assert sol.itens.count() == 1
        item_sol = sol.itens.first()
        assert item_sol.material_id == material.pk
        assert item_sol.quantidade == 2

    def test_nao_gera_se_nao_aprovado(self, pedido, material, usuario):
        ItemPedido.objects.create(
            pedido=pedido, material=material,
            quantidade=1, valor_unitario=Decimal("10.00"),
        )
        with pytest.raises(ValidationError):
            pedido.gerar_solicitacao_compra(usuario)

    def test_nao_gera_sem_itens(self, pedido, usuario):
        pedido.status = Pedido.StatusChoices.APROVADO
        pedido.save()
        with pytest.raises(ValidationError):
            pedido.gerar_solicitacao_compra(usuario)

    def test_nao_gera_duas_vezes(self, pedido, material, usuario):
        self._pedido_aprovado_com_item(pedido, material, usuario)
        pedido.gerar_solicitacao_compra(usuario)
        pedido.status = Pedido.StatusChoices.APROVADO  # forÃ§a re-tentativa
        with pytest.raises(ValidationError):
            pedido.gerar_solicitacao_compra(usuario)


class TestSolicitacaoCompra:
    @pytest.fixture
    def solicitacao(self, pedido, material, usuario):
        ItemPedido.objects.create(
            pedido=pedido, material=material,
            quantidade=2, valor_unitario=Decimal("10.00"),
        )
        pedido.status = Pedido.StatusChoices.APROVADO
        pedido.save()
        return pedido.gerar_solicitacao_compra(usuario)

    def test_numero_gerado(self, solicitacao):
        prefixo = f"SOL-{timezone.now().strftime('%Y%m')}"
        assert solicitacao.numero.startswith(prefixo)

    def test_status_inicial_fazer_cotacao(self, solicitacao):
        assert solicitacao.status == SolicitacaoCompra.StatusChoices.FAZER_COTACAO

    def test_dias_em_aberto(self, solicitacao):
        assert solicitacao.dias_em_aberto == 0

    def test_pode_cancelar(self, solicitacao):
        assert solicitacao.pode_cancelar is True
        solicitacao.status = SolicitacaoCompra.StatusChoices.FINALIZADO
        assert solicitacao.pode_cancelar is False

    def test_todos_itens_cotados_falso_sem_cotacao(self, solicitacao):
        assert solicitacao.todos_itens_cotados is False

    def test_etapa_atual(self, solicitacao):
        assert solicitacao.etapa_atual == 1


    @pytest.fixture
    def item_sol(self, pedido, material, usuario):
        ItemPedido.objects.create(
            pedido=pedido, material=material,
            quantidade=10, valor_unitario=Decimal("10.00"),
        )
        pedido.status = Pedido.StatusChoices.APROVADO
        pedido.save()
        sol = pedido.gerar_solicitacao_compra(usuario)
        return sol.itens.first()

    def test_valor_total(self, item_sol, fornecedor, usuario):
        cot = Cotacao.objects.create(
            item_solicitacao=item_sol, fornecedor=fornecedor,
            valor_unitario=Decimal("9.50"), criado_por=usuario,
        )
        # quantidade do item = 10
        assert cot.valor_total == Decimal("95.00")

    def test_menor_cotacao(self, item_sol, fornecedor, fornecedor_b, usuario):
        Cotacao.objects.create(
            item_solicitacao=item_sol, fornecedor=fornecedor,
            valor_unitario=Decimal("9.50"), criado_por=usuario,
        )
        c2 = Cotacao.objects.create(
            item_solicitacao=item_sol, fornecedor=fornecedor_b,
            valor_unitario=Decimal("8.00"), criado_por=usuario,
        )
        assert item_sol.menor_cotacao.pk == c2.pk
        assert c2.is_menor_preco is True

    def test_unique_fornecedor_por_item(self, item_sol, fornecedor, usuario):
        Cotacao.objects.create(
            item_solicitacao=item_sol, fornecedor=fornecedor,
            valor_unitario=Decimal("9.50"), criado_por=usuario,
        )
        with pytest.raises(IntegrityError):
            Cotacao.objects.create(
                item_solicitacao=item_sol, fornecedor=fornecedor,
                valor_unitario=Decimal("7.00"), criado_por=usuario,
            )

    def test_tem_cotacoes(self, item_sol, fornecedor, usuario):
        assert item_sol.tem_cotacoes is False
        Cotacao.objects.create(
            item_solicitacao=item_sol, fornecedor=fornecedor,
            valor_unitario=Decimal("9.50"), criado_por=usuario,
        )
        assert item_sol.tem_cotacoes is True


class TestPedidoCompra:
    @pytest.fixture
    def pc(self, pedido, material, fornecedor, filial, usuario):
        ItemPedido.objects.create(
            pedido=pedido, material=material,
            quantidade=10, valor_unitario=Decimal("10.00"),
        )
        pedido.status = Pedido.StatusChoices.APROVADO
        pedido.save()
        sol = pedido.gerar_solicitacao_compra(usuario)
        return PedidoCompra.objects.create(
            solicitacao=sol, fornecedor=fornecedor, filial=filial,
            criado_por=usuario,
        )

    def test_numero_gerado(self, pc):
        prefixo = f"PC-{timezone.now().strftime('%Y%m')}"
        assert pc.numero.startswith(prefixo)

    def test_recalcular_total(self, pc, material, usuario):
        item_sol = pc.solicitacao.itens.first()
        cot = Cotacao.objects.create(
            item_solicitacao=item_sol,
            fornecedor=pc.fornecedor,
            valor_unitario=Decimal("9.00"),
            criado_por=usuario,
        )
        ItemPedidoCompra.objects.create(
            pedido_compra=pc, cotacao=cot, item_solicitacao=item_sol,
            material=material, quantidade=Decimal("10"),
            valor_unitario=Decimal("9.00"),
        )
        pc.refresh_from_db()
        assert pc.valor_total == Decimal("90.00")

    def test_item_valor_total_e_saldo(self, pc, material, usuario):
        item_sol = pc.solicitacao.itens.first()
        cot = Cotacao.objects.create(
            item_solicitacao=item_sol, fornecedor=pc.fornecedor,
            valor_unitario=Decimal("9.00"), criado_por=usuario,
        )
        item = ItemPedidoCompra.objects.create(
            pedido_compra=pc, cotacao=cot, item_solicitacao=item_sol,
            material=material, quantidade=Decimal("10"),
            valor_unitario=Decimal("9.00"),
        )
        assert item.valor_total == Decimal("90.00")
        assert item.saldo_receber == Decimal("10")
        assert item.recebimento_completo is False
        item.quantidade_recebida = Decimal("10")
        assert item.recebimento_completo is True

    def test_atualizar_status_entrega_parcial(self, pc, material, usuario):
        item_sol = pc.solicitacao.itens.first()
        cot = Cotacao.objects.create(
            item_solicitacao=item_sol, fornecedor=pc.fornecedor,
            valor_unitario=Decimal("9.00"), criado_por=usuario,
        )
        item = ItemPedidoCompra.objects.create(
            pedido_compra=pc, cotacao=cot, item_solicitacao=item_sol,
            material=material, quantidade=Decimal("10"),
            valor_unitario=Decimal("9.00"),
        )
        item.quantidade_recebida = Decimal("4")
        item.save(update_fields=["quantidade_recebida"])
        pc.atualizar_status_entrega()
        pc.refresh_from_db()
        assert pc.status == PedidoCompra.StatusPC.ENTREGA_PARCIAL

    def test_atualizar_status_entrega_completa(self, pc, material, usuario):
        item_sol = pc.solicitacao.itens.first()
        cot = Cotacao.objects.create(
            item_solicitacao=item_sol, fornecedor=pc.fornecedor,
            valor_unitario=Decimal("9.00"), criado_por=usuario,
        )
        item = ItemPedidoCompra.objects.create(
            pedido_compra=pc, cotacao=cot, item_solicitacao=item_sol,
            material=material, quantidade=Decimal("10"),
            valor_unitario=Decimal("9.00"),
        )
        item.quantidade_recebida = Decimal("10")
        item.save(update_fields=["quantidade_recebida"])
        pc.atualizar_status_entrega()
        pc.refresh_from_db()
        assert pc.status == PedidoCompra.StatusPC.ENTREGUE
        assert pc.data_entrega_efetiva is not None

    def test_pode_cancelar(self, pc):
        assert pc.pode_cancelar is True
        pc.status = PedidoCompra.StatusPC.RECEBIDO
        assert pc.pode_cancelar is False


class TestEstoqueConsumo:
    def test_saldo_material(self, material, contrato, filial, usuario):
        EstoqueConsumo.objects.create(
            material=material, contrato=contrato, filial=filial,
            tipo=EstoqueConsumo.TipoMovimento.ENTRADA,
            quantidade=100, responsavel=usuario,
        )
        EstoqueConsumo.objects.create(
            material=material, contrato=contrato, filial=filial,
            tipo=EstoqueConsumo.TipoMovimento.SAIDA,
            quantidade=30, responsavel=usuario,
        )
        saldo = EstoqueConsumo.saldo_material(
            material.id, contrato.id, filial.id,
        )
        assert saldo == 70

    def test_str(self, material, contrato, filial, usuario):
        mov = EstoqueConsumo.objects.create(
            material=material, contrato=contrato, filial=filial,
            tipo=EstoqueConsumo.TipoMovimento.ENTRADA,
            quantidade=10, responsavel=usuario,
        )
        assert "Entrada" in str(mov)


# pytest suprimentos/tests/test_models.py -v

