
# suprimentos/tests/test_geracao_solicitacao.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from suprimentos.models import Pedido, SolicitacaoCompra


class GeracaoSolicitacaoTest(TestCase):
    def setUp(self):
        U = get_user_model()
        self.aprovador = U.objects.create_user(
            username="aprovador_teste", password="x"
        )
        # ... criar pedido PENDENTE com itens ...

    def test_aprovar_pedido_gera_solicitacao_fazer_cotacao(self):
        pedido = self._criar_pedido_com_itens(qtd_itens=4)
        pedido.status = Pedido.StatusChoices.APROVADO
        pedido.aprovador = self.aprovador
        pedido.save()  # dispara o signal

        pedido.refresh_from_db()
        sol = pedido.solicitacao_gerada

        self.assertIsNotNone(sol)
        self.assertEqual(sol.status, SolicitacaoCompra.StatusChoices.FAZER_COTACAO)
        self.assertEqual(sol.itens.count(), 4)

    def test_idempotencia_nao_duplica_solicitacao(self):
        pedido = self._criar_pedido_com_itens(qtd_itens=2)
        sol1 = pedido.gerar_solicitacao_compra(usuario=self.aprovador)
        sol2 = pedido.gerar_solicitacao_compra(usuario=self.aprovador)
        self.assertEqual(sol1.pk, sol2.pk)  # mesma solicitação
