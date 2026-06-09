
# suprimentos/tests/test_pc_entrega.py
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages

from usuario.models import Filial
from suprimentos.models import (
    Contrato, Parceiro, Material, CategoriaMaterial, TipoMaterial,
    Pedido, ItemPedido, SolicitacaoCompra, ItemSolicitacao,
    Cotacao, PedidoCompra, ItemPedidoCompra,
)

User = get_user_model()


class BasePCEntregaTestCase(TestCase):
    """
    Monta toda a cadeia necessária:
    Filial → Contrato → Material → Pedido → Solicitação →
    ItemSolicitação → Cotação → PedidoCompra → ItemPedidoCompra
    """

    @classmethod
    def setUpTestData(cls):
        # ── Usuário com permissão de recebimento ──────────────
        cls.user = User.objects.create_user(
            username="emerson", password="senha-teste-123",
        )
        perm = Permission.objects.get(codename="pode_receber_pedido_compra")
        cls.user.user_permissions.add(perm)

        # ── Filial / Contrato / Fornecedor ────────────────────
        cls.filial = Filial.objects.create(nome="Filial Teste")

        cls.contrato = Contrato.objects.create(
            cm="CM-0001", cliente="Cliente Teste", filial=cls.filial,
        )
        cls.fornecedor = Parceiro.objects.create(
            nome_fantasia="Fornecedor Teste",
            razao_social="Fornecedor Teste LTDA",
            cnpj="03.244.478/0003-17",
            eh_fornecedor=True, ativo=True, filial=cls.filial,
        )

        # ── Materiais ─────────────────────────────────────────
        cls.material_a = Material.objects.create(
            descricao="COLA INSTANTANEA",
            classificacao=CategoriaMaterial.CONSUMO,
            tipo=TipoMaterial.LIMPEZA,
            valor_unitario=Decimal("10.00"),
            filial=cls.filial,
        )
        cls.material_b = Material.objects.create(
            descricao="FITA ALUMINIZADA 50MM X 30M",
            classificacao=CategoriaMaterial.CONSUMO,
            tipo=TipoMaterial.LIMPEZA,
            valor_unitario=Decimal("20.00"),
            filial=cls.filial,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        self._montar_pedido_compra()
        self.url = reverse(
            "suprimentos:pc_acompanhar_entrega", kwargs={"pk": self.pc.pk}
        )

    # ──────────────────────────────────────────────────────────
    def _montar_pedido_compra(self):
        """Cria PC com 2 itens (qtd 10 e 5), pronto para recebimento."""
        pedido = Pedido.objects.create(
            contrato=self.contrato,
            filial=self.filial,
            solicitante=self.user,
            status=Pedido.StatusChoices.APROVADO,
        )
        ip_a = ItemPedido.objects.create(
            pedido=pedido, material=self.material_a,
            quantidade=10, valor_unitario=Decimal("10.00"),
        )
        ip_b = ItemPedido.objects.create(
            pedido=pedido, material=self.material_b,
            quantidade=5, valor_unitario=Decimal("20.00"),
        )

        self.sol = SolicitacaoCompra.objects.create(
            pedido=pedido,
            filial=self.filial,
            solicitante=self.user,
            contrato=self.contrato,
            tipo_obra="CM",
            descricao_material="Teste de recebimento",
            status=SolicitacaoCompra.StatusChoices.PEDIDO_GERADO,
            usa_novo_fluxo=True,
        )

        isol_a = ItemSolicitacao.objects.create(
            solicitacao=self.sol, item_pedido_origem=ip_a,
            material=self.material_a, quantidade=Decimal("10.00"),
            valor_unitario_estimado=Decimal("10.00"),
            status=ItemSolicitacao.StatusItem.APROVADO,
        )
        isol_b = ItemSolicitacao.objects.create(
            solicitacao=self.sol, item_pedido_origem=ip_b,
            material=self.material_b, quantidade=Decimal("5.00"),
            valor_unitario_estimado=Decimal("20.00"),
            status=ItemSolicitacao.StatusItem.APROVADO,
        )

        cot_a = Cotacao.objects.create(
            item_solicitacao=isol_a, fornecedor=self.fornecedor,
            valor_unitario=Decimal("10.00"), criado_por=self.user,
        )
        cot_b = Cotacao.objects.create(
            item_solicitacao=isol_b, fornecedor=self.fornecedor,
            valor_unitario=Decimal("20.00"), criado_por=self.user,
        )
        isol_a.cotacao_escolhida = cot_a
        isol_b.cotacao_escolhida = cot_b
        isol_a.save(update_fields=["cotacao_escolhida"])
        isol_b.save(update_fields=["cotacao_escolhida"])

        self.pc = PedidoCompra.objects.create(
            solicitacao=self.sol,
            fornecedor=self.fornecedor,
            filial=self.filial,
            status=PedidoCompra.StatusPC.ENVIADO_FORNECEDOR,
            criado_por=self.user,
        )
        self.item_a = ItemPedidoCompra.objects.create(
            pedido_compra=self.pc, cotacao=cot_a, item_solicitacao=isol_a,
            material=self.material_a, quantidade=Decimal("10.00"),
            valor_unitario=Decimal("10.00"),
        )
        self.item_b = ItemPedidoCompra.objects.create(
            pedido_compra=self.pc, cotacao=cot_b, item_solicitacao=isol_b,
            material=self.material_b, quantidade=Decimal("5.00"),
            valor_unitario=Decimal("20.00"),
        )


# ═════════════════════════════════════════════════════════════
# TESTES — todos numa única classe que herda da Base
# ═════════════════════════════════════════════════════════════
class PCEntregaTests(BasePCEntregaTestCase):

    # 1) Setup íntegro
    def test_setup_integro(self):
        self.assertEqual(self.pc.itens.count(), 2)
        self.assertEqual(self.item_a.saldo, Decimal("10.00"))
        self.assertEqual(self.item_b.saldo, Decimal("5.00"))
        self.assertEqual(self.pc.valor_total, Decimal("200.00"))

    # 2) GET — página carrega
    def test_get_pagina_entrega(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "COLA INSTANTANEA")
        self.assertContains(resp, "FITA ALUMINIZADA")

    # 3) Recebimento PARCIAL → status ENTREGA_PARCIAL
    def test_recebimento_parcial(self):
        self.client.post(self.url, {
            f"recebido_{self.item_a.pk}": "4",
        })
        self.item_a.refresh_from_db()
        self.pc.refresh_from_db()

        self.assertEqual(self.item_a.quantidade_recebida, Decimal("4.00"))
        self.assertEqual(self.item_a.saldo, Decimal("6.00"))
        self.assertEqual(self.pc.status, PedidoCompra.StatusPC.ENTREGA_PARCIAL)
        self.assertEqual(self.pc.recebido_por, self.user)

    # 4) Recebimento TOTAL → status ENTREGUE + data efetiva
    def test_recebimento_total(self):
        self.client.post(self.url, {
            f"recebido_{self.item_a.pk}": "10",
            f"recebido_{self.item_b.pk}": "5",
        })
        self.item_a.refresh_from_db()
        self.item_b.refresh_from_db()
        self.pc.refresh_from_db()

        self.assertEqual(self.item_a.saldo, Decimal("0.00"))
        self.assertEqual(self.item_b.saldo, Decimal("0.00"))
        self.assertEqual(self.pc.status, PedidoCompra.StatusPC.ENTREGUE)
        self.assertIsNotNone(self.pc.data_entrega_efetiva)

    # 5) Acima do saldo → bloqueia, rollback (nada gravado)
    def test_recebimento_acima_do_saldo_bloqueia(self):
        # POST com 15 (saldo do item_a é 10) → deve estourar
        resposta = self.client.post(self.url, {
            f"recebido_{self.item_a.pk}": "15",
        })

        self.item_a.refresh_from_db()
        self.pc.refresh_from_db()

        # ── Asserções: NADA foi gravado ──
        self.assertEqual(self.item_a.quantidade_recebida, Decimal("0.00"))
        self.assertEqual(self.pc.status, PedidoCompra.StatusPC.ENVIADO_FORNECEDOR)

        self.assertRedirects(resposta, self.url, fetch_redirect_response=False)

        mensagens = [str(m) for m in get_messages(resposta.wsgi_request)]
        self.assertTrue(any("maior que o saldo" in m for m in mensagens))

    # 6) Recebimento ACUMULA (parcial → completa)
    def test_recebimento_acumula_em_duas_etapas(self):
        # 1ª etapa
        self.client.post(self.url, {
            f"recebido_{self.item_a.pk}": "6",
            f"recebido_{self.item_b.pk}": "5",
        })
        self.item_a.refresh_from_db()
        self.pc.refresh_from_db()
        self.assertEqual(self.item_a.saldo, Decimal("4.00"))
        self.assertEqual(self.pc.status, PedidoCompra.StatusPC.ENTREGA_PARCIAL)

        # 2ª etapa — completa o item A
        self.client.post(self.url, {
            f"recebido_{self.item_a.pk}": "4",
        })
        self.item_a.refresh_from_db()
        self.pc.refresh_from_db()
        self.assertEqual(self.item_a.quantidade_recebida, Decimal("10.00"))
        self.assertEqual(self.pc.status, PedidoCompra.StatusPC.ENTREGUE)

    # 7) Valor decimal com vírgula (pt-BR) é aceito
    def test_recebimento_valor_com_virgula(self):
        self.client.post(self.url, {
            f"recebido_{self.item_a.pk}": "2,50",
        })
        self.item_a.refresh_from_db()
        self.assertEqual(self.item_a.quantidade_recebida, Decimal("2.50"))

    # 8) POST vazio → não grava nada, status permanece
    def test_post_sem_quantidades(self):
        self.client.post(self.url, {})
        self.item_a.refresh_from_db()
        self.item_b.refresh_from_db()
        self.assertEqual(self.item_a.quantidade_recebida, Decimal("0.00"))
        self.assertEqual(self.item_b.quantidade_recebida, Decimal("0.00"))

    # 9) PC já finalizado → bloqueia novo recebimento
    def test_pc_finalizado_bloqueia(self):
        self.pc.status = PedidoCompra.StatusPC.ENTREGUE
        self.pc.save(update_fields=["status"])

        resp = self.client.get(self.url, follow=True)
        self.assertRedirects(
            resp, reverse("suprimentos:pc_detalhe", kwargs={"pk": self.pc.pk})
        )

    # 10) Sem permissão → 403
    def test_sem_permissao_403(self):
        outro = User.objects.create_user(
            username="outro_user",
            email="outro_unico@teste.com",
            password="senha123",
        )
        self.client.force_login(outro)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    # 11) Sem login → redireciona p/ login
    def test_sem_login_redireciona(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, (302, 403))


# .\run_tests.ps1 suprimentos.tests.test_pc_entrega
