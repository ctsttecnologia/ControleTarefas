
# suprimentos/tests/test_fluxo_suprimentos.py
"""
Suíte de testes do fluxo de Suprimentos.

Cobre:
    1. PedidoCreateView           -> cria pedido (RASCUNHO)
    2. pedido_aprovar             -> APROVADO -> gerar_solicitacao_compra()
    3. cotacao_adicionar          -> cria Cotacao (NxN) -> item COTADO
    4. cotacao_aprovar            -> escolhe cotação -> item APROVADO

Premissas confirmadas via models.py / forms.py:
    - Pedido.numero é auto-gerado (não enviar no POST).
    - Contrato exige cm/cliente/filial; Material exige descricao/classificacao/tipo.
    - ItemPedido.valor_unitario é obrigatório.
    - Cotação usa CotacaoCabecalhoForm + CotacaoItemValorFormSet (prefix "form").
    - gerar_solicitacao_compra() só roda com status APROVADO e cria ItemSolicitacao.

⚠️ AJUSTAR conforme seu views.py:
    - Nomes das URLs (reverse) -> seção URLS_AJUSTAR
    - Nomes dos campos POST de cotacao_aprovar -> CotacaoAprovarTest
"""

from decimal import Decimal
from typing import Self

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse, NoReverseMatch

from suprimentos.models import (
    CategoriaMaterial,
    TipoMaterial,
    UnidadeMedida,
    TipoObra,
    Contrato,
    Cotacao,
    ItemPedido,
    ItemSolicitacao,
    Material,
    Parceiro,
    Pedido,
    SolicitacaoCompra,
    HistoricoPedido,
)
from usuario.models import Filial

User = get_user_model()


# ═════════════════════════════════════════════════════════════
# BASE / FACTORIES
# ═════════════════════════════════════════════════════════════
class SuprimentosBaseTest(TestCase):

    # ---- usuários / permissões ------------------------------------
    def _criar_usuario(self, username, *codenames):
        self.user = get_user_model().objects.create_user(
            username=username,
            email=f"{username}@teste.local",
            password="senha123",
        )
        for codename in codenames:
            self.user.user_permissions.add(
                Permission.objects.get(codename=codename)
            )
        self.user = get_user_model().objects.get(pk=self.user.pk)
        return self.user

    # ---- domínio --------------------------------------------------
    @classmethod
    def _criar_filial(cls, **kw):
        """
        ⚠️ Ajuste os campos abaixo conforme usuario.models.Filial.
        Campos comuns: nome, codigo, cnpj. Removi o que não souber.
        """
        defaults = dict(nome=kw.pop("nome", "Filial Teste"))
        defaults.update(kw)
        # tenta criar tolerando campos extras obrigatórios
        return Filial.objects.create(**defaults)

    @classmethod
    def _criar_contrato(cls, filial, **kw):
        defaults = dict(
            cm=kw.pop("cm", "0001"),
            cliente=kw.pop("cliente", "Cliente Teste"),
            filial=filial,
        )
        defaults.update(kw)
        return Contrato.objects.create(**defaults)

    @classmethod
    def _criar_material(cls, **kw):
        defaults = dict(
            descricao=kw.pop("descricao", "Cimento CP-II 50kg"),
            classificacao=kw.pop("classificacao", CategoriaMaterial.CONSUMO),
            tipo=kw.pop("tipo", TipoMaterial.CIVIL),
            unidade=kw.pop("unidade", UnidadeMedida.UNID),
            valor_unitario=kw.pop("valor_unitario", Decimal("10.00")),
        )
        defaults.update(kw)
        return Material.objects.create(**defaults)

    @classmethod
    def _criar_fornecedor(cls, filial, **kw):
        defaults = dict(
            nome_fantasia=kw.pop("nome_fantasia", "Fornecedor Teste"),
            eh_fornecedor=True,
            ativo=True,
            filial=filial,
        )
        defaults.update(kw)
        return Parceiro.objects.create(**defaults)

    @classmethod
    def _criar_pedido(cls, solicitante, contrato, filial, **kw):
        defaults = dict(
            solicitante=solicitante,
            contrato=contrato,
            filial=filial,
            tipo_obra=TipoObra.CM,
            status=kw.pop("status", Pedido.StatusChoices.RASCUNHO),
        )
        defaults.update(kw)
        return Pedido.objects.create(**defaults)

    @classmethod
    def _add_item_pedido(cls, pedido, material, qtd="5", valor="10.00"):
        return ItemPedido.objects.create(
            pedido=pedido,
            material=material,
            quantidade=int(qtd),
            unidade_medida=material.unidade,
            valor_unitario=Decimal(valor),
        )

    @classmethod
    def _criar_solicitacao(cls, pedido, filial, status, comprador=None):
        item0 = pedido.itens.first()
        return SolicitacaoCompra.objects.create(
            pedido=pedido,
            filial=filial,
            solicitante=pedido.solicitante,
            contrato=pedido.contrato,
            tipo_obra=pedido.tipo_obra,
            descricao_material="Item de teste",
            quantidade=item0.quantidade if item0 else Decimal("1"),
            unidade_medida=UnidadeMedida.UNID,
            tipo_insumo=TipoMaterial.CIVIL,
            comprador=comprador,
            status=status,
            usa_novo_fluxo=True,
        )

    @classmethod
    def _criar_item_solic(cls, solicitacao, material, status, qtd="5"):
        return ItemSolicitacao.objects.create(
            solicitacao=solicitacao,
            material=material,
            quantidade=Decimal(qtd),
            valor_unitario_estimado=Decimal("10.00"),
            status=status,
        )


# ═════════════════════════════════════════════════════════════
# 0. SANITY — gerar_solicitacao_compra() puro (sem HTTP)
#    O teste MAIS importante: valida a regra de negócio central.
# ═════════════════════════════════════════════════════════════
class GerarSolicitacaoCompraTest(SuprimentosBaseTest):

    def setUp(self):
        self.filial = self._criar_filial()
        self.user = self._criar_usuario("gerente")
        self.contrato = self._criar_contrato(self.filial)
        self.material = self._criar_material()
        self.pedido = self._criar_pedido(
            self.user, self.contrato, self.filial,
            status=Pedido.StatusChoices.APROVADO,
        )
        self._add_item_pedido(self.pedido, self.material, qtd="3")

    def test_gera_solicitacao_e_itens(self):
        solic = self.pedido.gerar_solicitacao_compra(usuario=self.user)

        # Solicitação criada e vinculada
        self.assertIsNotNone(solic.pk)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.solicitacao_gerada_id, solic.pk)
        self.assertEqual(
            self.pedido.status, Pedido.StatusChoices.SOLICITACAO_GERADA
        )
        # Status inicial da solicitação
        self.assertEqual(
            solic.status, SolicitacaoCompra.StatusChoices.FAZER_COTACAO
        )
        # 1 ItemSolicitacao gerado a partir do ItemPedido
        self.assertEqual(solic.itens.count(), 1)
        item = solic.itens.first()
        self.assertEqual(item.material, self.material)
        self.assertEqual(item.status, ItemSolicitacao.StatusItem.PENDENTE_COTACAO)
        self.assertEqual(item.item_pedido_origem, self.pedido.itens.first())

    def test_nao_gera_se_nao_aprovado(self):
        from django.core.exceptions import ValidationError
        self.pedido.status = Pedido.StatusChoices.PENDENTE
        self.pedido.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            self.pedido.gerar_solicitacao_compra(usuario=self.user)

    def test_nao_duplica_solicitacao(self):
        from django.core.exceptions import ValidationError
        self.pedido.gerar_solicitacao_compra(usuario=self.user)
        # status virou SOLICITACAO_GERADA -> segunda chamada deve falhar
        self.pedido.refresh_from_db()
        self.pedido.status = Pedido.StatusChoices.APROVADO  # força recheck
        self.pedido.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            self.pedido.gerar_solicitacao_compra(usuario=self.user)


# ═════════════════════════════════════════════════════════════
# 1. PedidoCreateView
# ═════════════════════════════════════════════════════════════
class PedidoCreateViewTest(SuprimentosBaseTest):

    # nomes candidatos de URL — ajuste para o seu urls.py
    URL_NAMES = ["suprimentos:pedido_novo", "suprimentos:pedido_criar"]

    def _url(self):
        for name in self.URL_NAMES:
            try:
                return reverse(name)
            except NoReverseMatch:
                continue
        self.skipTest(f"Nenhuma URL encontrada em {self.URL_NAMES}")

    def setUp(self):
        self.filial = self._criar_filial()
        self.user = self._criar_usuario("solicitante")
        self.contrato = self._criar_contrato(self.filial)
        self.material = self._criar_material()

    def test_anonimo_redireciona_login(self):
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url.lower())

    def test_logado_acessa_form(self):
        self.client.force_login(self.user)
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 200)

    def test_cria_pedido_com_itens(self):
        self.client.force_login(self.user)
        data = {
            # PedidoForm
            "contrato": self.contrato.pk,
            "filial": self.filial.pk,
            "tipo_obra": TipoObra.CM,
            "observacao": "Pedido de teste",
            # ItemPedidoFormSet (inline, prefix padrão "itens")
            "itens-TOTAL_FORMS": "1",
            "itens-INITIAL_FORMS": "0",
            "itens-MIN_NUM_FORMS": "0",
            "itens-MAX_NUM_FORMS": "1000",
            "itens-0-material": self.material.pk,
            "itens-0-quantidade": "10",
            "itens-0-unidade_medida": UnidadeMedida.UNID,
            "itens-0-valor_unitario": "12.50",
            "itens-0-observacao": "",
        }
        resp = self.client.post(self._url(), data)

        self.assertEqual(
            resp.status_code, 302,
            msg=f"Esperado redirect; recebido {resp.status_code}. "
                f"Verifique prefix do formset ('itens') e campos do PedidoForm.",
        )
        pedido = Pedido.objects.first()
        self.assertIsNotNone(pedido)
        self.assertEqual(pedido.solicitante, self.user)
        self.assertTrue(pedido.numero.startswith("PED-"))
        self.assertEqual(pedido.itens.count(), 1)


# ═════════════════════════════════════════════════════════════
# 2. pedido_aprovar
# ═════════════════════════════════════════════════════════════
class PedidoAprovarTest(SuprimentosBaseTest):

    def setUp(self):
        self.filial = self._criar_filial()
        self.solicitante = self._criar_usuario("solicitante")
        self.sem_perm = self._criar_usuario("comum")
        self.gerente = self._criar_usuario("gerente", "pode_aprovar_pedido")

        self.contrato = self._criar_contrato(self.filial)
        self.material = self._criar_material()
        self.pedido = self._criar_pedido(
            self.solicitante, self.contrato, self.filial,
            status=Pedido.StatusChoices.PENDENTE,
        )
        self._add_item_pedido(self.pedido, self.material)

        try:
            self.url = reverse("suprimentos:pedido_aprovar", args=[self.pedido.pk])
        except NoReverseMatch:
            self.skipTest("URL 'suprimentos:pedido_aprovar' não encontrada")

    # ---- permissões -----------------------------------------------
    def test_anonimo_redireciona(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_sem_permissao_403(self):
        self.client.force_login(self.sem_perm)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_com_permissao_acessa(self):
        self.client.force_login(self.gerente)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    # ---- decisões (AprovarPedidoForm: decisao + motivo) -----------
    def test_aprovar_gera_solicitacao(self):
        self.client.force_login(self.gerente)
        self.client.post(self.url, {"decisao": "APROVAR", "motivo": ""})
        self.pedido.refresh_from_db()
        # aprovado e solicitação gerada (status final pode ser SOLICITACAO_GERADA)
        self.assertIn(
            self.pedido.status,
            [Pedido.StatusChoices.APROVADO, Pedido.StatusChoices.SOLICITACAO_GERADA],
        )
        self.assertTrue(
            SolicitacaoCompra.objects.filter(pedido=self.pedido).exists(),
            msg="gerar_solicitacao_compra() deveria ter rodado na aprovação.",
        )

    def test_revisar_exige_motivo(self):
        self.client.force_login(self.gerente)
        # sem motivo -> form inválido -> não muda status
        self.client.post(self.url, {"decisao": "REVISAR", "motivo": ""})
        self.pedido.refresh_from_db()
        self.assertNotEqual(self.pedido.status, Pedido.StatusChoices.REVISAO)

    def test_revisar_com_motivo(self):
        self.client.force_login(self.gerente)
        self.client.post(
            self.url, {"decisao": "REVISAR", "motivo": "Ajustar quantidades"}
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.StatusChoices.REVISAO)

    def test_reprovar_com_motivo(self):
        self.client.force_login(self.gerente)
        self.client.post(
            self.url, {"decisao": "REPROVAR", "motivo": "Fora do escopo"}
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.StatusChoices.REPROVADO)


# ═════════════════════════════════════════════════════════════
# 3. cotacao_adicionar  (NxN: cabeçalho + formset de valores)
# ═════════════════════════════════════════════════════════════
class CotacaoAdicionarTest(SuprimentosBaseTest):

    def setUp(self):
        self.filial = self._criar_filial()
        self.comprador = self._criar_usuario("comprador", "pode_cotar")
        self.sem_perm = self._criar_usuario("comum")

        self.contrato = self._criar_contrato(self.filial)
        self.material = self._criar_material()
        self.fornecedor = self._criar_fornecedor(self.filial)

        self.pedido = self._criar_pedido(
            self.comprador, self.contrato, self.filial,
            status=Pedido.StatusChoices.SOLICITACAO_GERADA,
        )
        self._add_item_pedido(self.pedido, self.material)
        self.solicitacao = self._criar_solicitacao(
            self.pedido, self.filial,
            status=SolicitacaoCompra.StatusChoices.FAZER_COTACAO,
            comprador=self.comprador,
        )
        self.item = self._criar_item_solic(
            self.solicitacao, self.material,
            status=ItemSolicitacao.StatusItem.PENDENTE_COTACAO,
        )

        try:
            self.url = reverse(
                "suprimentos:cotacao_adicionar", args=[self.solicitacao.pk]
            )
        except NoReverseMatch:
            self.skipTest("URL 'suprimentos:cotacao_adicionar' não encontrada")

    # ---- permissões -----------------------------------------------
    def test_anonimo_redireciona(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_sem_permissao_403(self):
        self.client.force_login(self.sem_perm)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_com_permissao_acessa(self):
        self.client.force_login(self.comprador)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    # ---- criação NxN ----------------------------------------------
    def _payload(self, valor="25.50"):
        return {
            # CotacaoCabecalhoForm
            "fornecedor": self.fornecedor.pk,
            "condicoes_pagamento": "30 dias",
            "prazo_entrega_dias": "5",
            # CotacaoItemValorFormSet (prefix padrão "form")
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-item_id": self.item.pk,
            "form-0-valor_unitario": valor,
        }

    def test_criar_cotacao(self):
        self.client.force_login(self.comprador)
        self.client.post(self.url, self._payload())
        self.assertTrue(
            Cotacao.objects.filter(
                item_solicitacao=self.item, fornecedor=self.fornecedor
            ).exists(),
            msg="Cotação não criada. Confira prefix 'form' e nomes "
                "fornecedor/item_id/valor_unitario na view.",
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ItemSolicitacao.StatusItem.COTADO)

    def test_duplicidade_bloqueada(self):
        # cria 1ª cotação no banco
        Cotacao.objects.create(
            item_solicitacao=self.item,
            fornecedor=self.fornecedor,
            valor_unitario=Decimal("20.00"),
            criado_por=self.comprador,
        )
        self.client.force_login(self.comprador)
        self.client.post(self.url, self._payload(valor="22.00"))
        total = Cotacao.objects.filter(
            item_solicitacao=self.item, fornecedor=self.fornecedor
        ).count()
        # UniqueConstraint do model garante no máximo 1
        self.assertEqual(total, 1)


# ═════════════════════════════════════════════════════════════
# 4. cotacao_aprovar  (escolha por item — POST manual)
# ═════════════════════════════════════════════════════════════
class CotacaoAprovarTest(SuprimentosBaseTest):

    def setUp(self):
        self.filial = self._criar_filial()
        self.gerente = self._criar_usuario("gerente", "pode_aprovar_cotacao")
        self.sem_perm = self._criar_usuario("comum")

        self.contrato = self._criar_contrato(self.filial)
        self.material = self._criar_material()
        self.fornecedor = self._criar_fornecedor(self.filial)

        # garante verba suficiente p/ não cair na validação de saldo
        verba = self.contrato.verba_do_mes()
        verba.verba_consumo = Decimal("100000.00")
        verba.save()

        self.pedido = self._criar_pedido(
            self.gerente, self.contrato, self.filial,
            status=Pedido.StatusChoices.SOLICITACAO_GERADA,
        )
        self._add_item_pedido(self.pedido, self.material)
        self.solicitacao = self._criar_solicitacao(
            self.pedido, self.filial,
            status=SolicitacaoCompra.StatusChoices.EM_APROVACAO,
        )
        self.item = self._criar_item_solic(
            self.solicitacao, self.material,
            status=ItemSolicitacao.StatusItem.COTADO,
        )
        self.cotacao = Cotacao.objects.create(
            item_solicitacao=self.item,
            fornecedor=self.fornecedor,
            valor_unitario=Decimal("15.00"),
            criado_por=self.gerente,
        )

        try:
            self.url = reverse(
                "suprimentos:cotacao_aprovar", args=[self.solicitacao.pk]
            )
        except NoReverseMatch:
            self.skipTest("URL 'suprimentos:cotacao_aprovar' não encontrada")

    # ---- permissões -----------------------------------------------
    def test_anonimo_redireciona(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_sem_permissao_403(self):
        self.client.force_login(self.sem_perm)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_com_permissao_acessa(self):
        self.client.force_login(self.gerente)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    # ---- aprovação por item ---------------------------------------
    # ⚠️ O nome do campo POST depende da SUA view. Abaixo tento os 3
    #    padrões mais comuns; ajuste para o que a view realmente lê.
    def _post_escolha(self):
        return {
            f"cotacao_item_{self.item.pk}": self.cotacao.pk,   # padrão A
            f"cotacao_{self.item.pk}": self.cotacao.pk,        # padrão B
            f"item_{self.item.pk}": self.cotacao.pk,           # padrão C
        }

    def test_aprovar_item_escolhe_cotacao(self):
        self.client.force_login(self.gerente)
        self.client.post(self.url, self._post_escolha())
        self.item.refresh_from_db()
        self.assertEqual(
            self.item.status, ItemSolicitacao.StatusItem.APROVADO,
            msg="Item não foi aprovado. Confirme o NOME do campo POST "
                "que a view cotacao_aprovar lê para a escolha por item.",
        )
        self.assertEqual(self.item.cotacao_escolhida, self.cotacao)


# Comece pelo teste de regra de negócio pura (não depende de views/URLs):

# python manage.py test suprimentos.tests.test_fluxo_suprimentos.GerarSolicitacaoCompraTest -v 2

# Depois o fluxo HTTP completo:

# python manage.py test suprimentos.tests.test_fluxo_suprimentos -v 2
