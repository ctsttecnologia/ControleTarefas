
# suprimentos/tests/test_signals.py
"""
Testes dos signals de suprimentos.

Estratégia:
- Funções auxiliares (_entrada_epi/_consumo/_ferramenta) são mockadas
  na maioria dos testes do dispatcher, para isolar a lógica de roteamento.
- Testes dedicados cobrem cada _entrada_* individualmente.
- _gerar_solicitacao_do_pedido tem testes próprios (idempotência, sem itens, sucesso).
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest

import suprimentos.signals as sig
from suprimentos.signals import (
    _gerar_solicitacao_do_pedido,
    pedido_aprovado_criar_solicitacao,
    pedido_recebido_gerar_entrada_estoque,
    _entrada_epi,
    _entrada_consumo,
    _entrada_ferramenta,
)


# ═══════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════
def _fake(**attrs):
    obj = MagicMock()
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


# ═══════════════════════════════════════════════
# _gerar_solicitacao_do_pedido
# ═══════════════════════════════════════════════
class TestGerarSolicitacao:

    @patch('suprimentos.signals.SolicitacaoCompra')
    def test_idempotencia_ja_existe(self, mock_sol):
        """Se já existe solicitação, retorna sem criar nada."""
        mock_sol.objects.filter.return_value.exists.return_value = True
        pedido = _fake(numero='PED-1')

        result = _gerar_solicitacao_do_pedido(pedido)

        assert result is None
        mock_sol.objects.create.assert_not_called()

    @patch('suprimentos.signals.SolicitacaoCompra')
    def test_pedido_sem_itens(self, mock_sol):
        """Pedido sem itens não gera solicitação."""
        mock_sol.objects.filter.return_value.exists.return_value = False
        pedido = _fake(numero='PED-2')
        pedido.itens.select_related.return_value.all.return_value.exists.return_value = False

        result = _gerar_solicitacao_do_pedido(pedido)

        assert result is None
        mock_sol.objects.create.assert_not_called()

    @patch('suprimentos.signals.ItemSolicitacao')
    @patch('suprimentos.signals.SolicitacaoCompra')
    def test_cria_solicitacao_com_itens(self, mock_sol, mock_item):
        """Caminho feliz: cria cabeçalho + itens e notifica."""
        mock_sol.objects.filter.return_value.exists.return_value = False

        item_ped = _fake(
            material=_fake(),
            quantidade=5,
            valor_unitario=Decimal('10'),
            observacao='obs',
        )
        itens_qs = MagicMock()
        itens_qs.exists.return_value = True
        itens_qs.__iter__.return_value = iter([item_ped])
        pedido = _fake(numero='PED-3')
        pedido.itens.select_related.return_value.all.return_value = itens_qs

        solicitacao = MagicMock(numero='SC-1')
        mock_sol.objects.create.return_value = solicitacao

        # transaction.atomic como context manager no-op
        with patch('suprimentos.signals.transaction'):
            # notificação ausente -> ImportError ramo
            result = _gerar_solicitacao_do_pedido(pedido)

        mock_sol.objects.create.assert_called_once()
        mock_item.objects.create.assert_called_once()
        assert result is solicitacao

    @patch('suprimentos.signals.ItemSolicitacao')
    @patch('suprimentos.signals.SolicitacaoCompra')
    def test_notificacao_import_indisponivel(self, mock_sol, mock_item):
        """Cobre o ramo ImportError (serviço de notificação ausente)."""
        mock_sol.objects.filter.return_value.exists.return_value = False
        item_ped = _fake(material=_fake(), quantidade=1,
                          valor_unitario=None, observacao=None)
        itens_qs = MagicMock()
        itens_qs.exists.return_value = True
        itens_qs.__iter__.return_value = iter([item_ped])
        pedido = _fake(numero='PED-IMP')
        pedido.itens.select_related.return_value.all.return_value = itens_qs
        mock_sol.objects.create.return_value = MagicMock(numero='SC-IMP')

        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == 'notifications.services':
                raise ImportError('sem notifications')
            return real_import(name, *args, **kwargs)

        with patch('suprimentos.signals.transaction'), \
             patch('builtins.__import__', side_effect=fake_import):
            result = _gerar_solicitacao_do_pedido(pedido)

        assert result is not None  # solicitação criada mesmo sem notificação


    @patch('suprimentos.signals.ItemSolicitacao')
    @patch('suprimentos.signals.SolicitacaoCompra')
    def test_notificacao_sucesso(self, mock_sol, mock_item):
        """Quando o serviço de notificação existe, ele é chamado."""
        mock_sol.objects.filter.return_value.exists.return_value = False
        item_ped = _fake(material=_fake(), quantidade=1,
                          valor_unitario=None, observacao=None)
        itens_qs = MagicMock()
        itens_qs.exists.return_value = True
        itens_qs.__iter__.return_value = iter([item_ped])
        pedido = _fake(numero='PED-4')
        pedido.itens.select_related.return_value.all.return_value = itens_qs
        mock_sol.objects.create.return_value = MagicMock(numero='SC-2')

        notif_mod = MagicMock()
        with patch('suprimentos.signals.transaction'), \
             patch.dict('sys.modules', {'notifications.services': notif_mod}):
            _gerar_solicitacao_do_pedido(pedido)

        notif_mod.notificar_solicitacao_criada.assert_called_once()

    @patch('suprimentos.signals.ItemSolicitacao')
    @patch('suprimentos.signals.SolicitacaoCompra')
    def test_notificacao_falha_nao_quebra(self, mock_sol, mock_item):
        """Falha na notificação é logada mas não derruba a solicitação."""
        mock_sol.objects.filter.return_value.exists.return_value = False
        item_ped = _fake(material=_fake(), quantidade=1,
                          valor_unitario=None, observacao=None)
        itens_qs = MagicMock()
        itens_qs.exists.return_value = True
        itens_qs.__iter__.return_value = iter([item_ped])
        pedido = _fake(numero='PED-5')
        pedido.itens.select_related.return_value.all.return_value = itens_qs
        solicitacao = MagicMock(numero='SC-3')
        mock_sol.objects.create.return_value = solicitacao

        notif_mod = MagicMock()
        notif_mod.notificar_solicitacao_criada.side_effect = RuntimeError('boom')
        with patch('suprimentos.signals.transaction'), \
             patch.dict('sys.modules', {'notifications.services': notif_mod}):
            result = _gerar_solicitacao_do_pedido(pedido)

        assert result is solicitacao  # não retornou None

    @patch('suprimentos.signals.CategoriaMaterial')
    @patch('suprimentos.signals.Pedido')
    def test_classificacao_desconhecida_ignorada(self, mock_pedido, mock_cat):
        """Item com classificação fora de EPI/CONSUMO/FERRAMENTA é pulado."""
        mock_cat.EPI = 'EPI'
        mock_cat.CONSUMO = 'CONSUMO'
        mock_cat.FERRAMENTA = 'FERRAMENTA'

        anterior = _fake(status='ENTREGUE')
        mock_pedido.objects.only.return_value.get.return_value = anterior
        mock_pedido.StatusChoices.ENTREGUE = 'ENTREGUE'
        mock_pedido.StatusChoices.RECEBIDO = 'RECEBIDO'

        mat = _fake(classificacao='OUTRO', grupo_tributario=None, descricao='?')
        item = _fake(material=mat, custo_real=Decimal('0.00'))
        inst = _fake(pk=1, estoque_processado=False, status='RECEBIDO',
                     numero='PED-DESC')
        inst.itens.select_related.return_value.all.return_value = [item]
        inst.contrato.filial = _fake()
        inst.recebedor_id = 1
        inst.solicitante_id = 2

        pedido_recebido_gerar_entrada_estoque(sender=None, instance=inst)
        assert inst.estoque_processado is True


    @patch('suprimentos.signals.SolicitacaoCompra')
    def test_excecao_geral_retorna_none(self, mock_sol):
        """Erro inesperado dentro do try -> log de erro e None."""
        mock_sol.objects.filter.return_value.exists.return_value = False

        # itens existe normalmente
        itens_qs = MagicMock()
        itens_qs.exists.return_value = True
        itens_qs.__iter__.return_value = iter([])
        pedido = _fake(numero='PED-6')
        pedido.itens.select_related.return_value.all.return_value = itens_qs

        # create estoura DENTRO do try/atomic
        mock_sol.objects.create.side_effect = RuntimeError('db down')

        with patch('suprimentos.signals.transaction'):
            result = _gerar_solicitacao_do_pedido(pedido)

        assert result is None


# ═══════════════════════════════════════════════
# pedido_aprovado_criar_solicitacao (receiver)
# ═══════════════════════════════════════════════
class TestReceiverAprovado:

    def test_ignora_created(self):
        """Em created=True não faz nada."""
        with patch('suprimentos.signals.transaction') as mock_tx:
            pedido_aprovado_criar_solicitacao(
                sender=None, instance=_fake(status='APROVADO'), created=True,
            )
        mock_tx.on_commit.assert_not_called()

    def test_ignora_status_diferente(self):
        """Status != APROVADO não agenda solicitação."""
        with patch('suprimentos.signals.transaction') as mock_tx:
            pedido_aprovado_criar_solicitacao(
                sender=None, instance=_fake(status='PENDENTE'), created=False,
            )
        mock_tx.on_commit.assert_not_called()

    def test_aprovado_agenda_on_commit(self):
        """APROVADO + update agenda _gerar via on_commit."""
        with patch('suprimentos.signals.transaction') as mock_tx:
            pedido_aprovado_criar_solicitacao(
                sender=None, instance=_fake(status='APROVADO'), created=False,
            )
        mock_tx.on_commit.assert_called_once()


# ═══════════════════════════════════════════════
# pedido_recebido_gerar_entrada_estoque (pre_save)
# ═══════════════════════════════════════════════
class TestReceiverRecebido:

    def test_sem_pk_ignora(self):
        inst = _fake(pk=None)
        pedido_recebido_gerar_entrada_estoque(sender=None, instance=inst)
        # nada a verificar além de não estourar
        assert True

    def test_estoque_ja_processado_ignora(self):
        inst = _fake(pk=1, estoque_processado=True)
        pedido_recebido_gerar_entrada_estoque(sender=None, instance=inst)
        assert True

    @patch('suprimentos.signals.Pedido')
    def test_pedido_anterior_nao_existe(self, mock_pedido):
        mock_pedido.DoesNotExist = Exception
        mock_pedido.objects.only.return_value.get.side_effect = \
            mock_pedido.DoesNotExist
        inst = _fake(pk=1, estoque_processado=False)
        pedido_recebido_gerar_entrada_estoque(sender=None, instance=inst)
        assert True

    @patch('suprimentos.signals.Pedido')
    def test_transicao_invalida_nao_processa(self, mock_pedido):
        """Anterior não está ENTREGUE -> ignora."""
        anterior = _fake(status='APROVADO')
        mock_pedido.objects.only.return_value.get.return_value = anterior
        mock_pedido.StatusChoices.ENTREGUE = 'ENTREGUE'
        mock_pedido.StatusChoices.RECEBIDO = 'RECEBIDO'
        inst = _fake(pk=1, estoque_processado=False, status='RECEBIDO')

        pedido_recebido_gerar_entrada_estoque(sender=None, instance=inst)
        assert inst.estoque_processado is False  # não chegou a marcar

    @patch('suprimentos.signals.ItemPedido')
    @patch('suprimentos.signals._entrada_epi')
    @patch('suprimentos.signals._entrada_consumo')
    @patch('suprimentos.signals._entrada_ferramenta')
    @patch('suprimentos.signals.CategoriaMaterial')
    @patch('suprimentos.signals.Pedido')
    def test_roteia_por_classificacao(
        self, mock_pedido, mock_cat, mock_ferr, mock_cons, mock_epi, mock_item,
    ):
        """ENTREGUE->RECEBIDO roteia cada item para a função certa."""
        mock_cat.EPI = 'EPI'
        mock_cat.CONSUMO = 'CONSUMO'
        mock_cat.FERRAMENTA = 'FERRAMENTA'

        anterior = _fake(status='ENTREGUE')
        mock_pedido.objects.only.return_value.get.return_value = anterior
        mock_pedido.StatusChoices.ENTREGUE = 'ENTREGUE'
        mock_pedido.StatusChoices.RECEBIDO = 'RECEBIDO'

        # 3 itens: um de cada categoria, sem grupo_tributario (pula recálculo)
        def mk_item(classif):
            mat = _fake(classificacao=classif, grupo_tributario=None,
                        descricao='x')
            return _fake(material=mat, custo_real=Decimal('0.00'))

        itens = [mk_item('EPI'), mk_item('CONSUMO'), mk_item('FERRAMENTA')]
        qs = MagicMock()
        qs.all.return_value = itens
        sel = MagicMock()
        sel.all.return_value = itens

        inst = _fake(pk=1, estoque_processado=False, status='RECEBIDO',
                     numero='PED-X')
        inst.itens.select_related.return_value.all.return_value = itens
        inst.contrato.filial = _fake()
        inst.recebedor_id = 7
        inst.solicitante_id = 9

        pedido_recebido_gerar_entrada_estoque(sender=None, instance=inst)

        mock_epi.assert_called_once()
        mock_cons.assert_called_once()
        mock_ferr.assert_called_once()
        assert inst.estoque_processado is True

    @patch('suprimentos.signals.ItemPedido')
    @patch('suprimentos.signals._entrada_consumo')
    @patch('suprimentos.signals.CategoriaMaterial')
    @patch('suprimentos.signals.Pedido')
    def test_recalcula_tributacao(
        self, mock_pedido, mock_cat, mock_cons, mock_item,
    ):
        """Item com grupo_tributario e custo_real=0 recalcula impostos."""
        mock_cat.EPI = 'EPI'
        mock_cat.CONSUMO = 'CONSUMO'
        mock_cat.FERRAMENTA = 'FERRAMENTA'

        anterior = _fake(status='ENTREGUE')
        mock_pedido.objects.only.return_value.get.return_value = anterior
        mock_pedido.StatusChoices.ENTREGUE = 'ENTREGUE'
        mock_pedido.StatusChoices.RECEBIDO = 'RECEBIDO'

        mat = _fake(classificacao='CONSUMO', grupo_tributario=_fake(),
                    descricao='Cimento')
        item = _fake(material=mat, custo_real=Decimal('0.00'), pk=42)
        item.calcular_impostos.return_value = {
            'custo_real': Decimal('80'),
            'total_creditos': Decimal('15'),
            'total_impostos': Decimal('20'),
        }

        inst = _fake(pk=1, estoque_processado=False, status='RECEBIDO',
                     numero='PED-Y')
        inst.itens.select_related.return_value.all.return_value = [item]
        inst.contrato.filial = _fake()
        inst.recebedor_id = None
        inst.solicitante_id = 3

        pedido_recebido_gerar_entrada_estoque(sender=None, instance=inst)

        item.calcular_impostos.assert_called_once()
        mock_item.objects.filter.assert_called_once_with(pk=42)
        mock_item.objects.filter.return_value.update.assert_called_once()

    @patch('suprimentos.signals._entrada_epi')
    @patch('suprimentos.signals.CategoriaMaterial')
    @patch('suprimentos.signals.Pedido')
    def test_erro_em_item_e_contabilizado(
        self, mock_pedido, mock_cat, mock_epi,
    ):
        """Exceção numa entrada é capturada (entradas_erro) sem derrubar."""
        mock_cat.EPI = 'EPI'
        anterior = _fake(status='ENTREGUE')
        mock_pedido.objects.only.return_value.get.return_value = anterior
        mock_pedido.StatusChoices.ENTREGUE = 'ENTREGUE'
        mock_pedido.StatusChoices.RECEBIDO = 'RECEBIDO'
        mock_epi.side_effect = RuntimeError('falha entrada')

        mat = _fake(classificacao='EPI', grupo_tributario=None, descricao='Luva')
        item = _fake(material=mat, custo_real=Decimal('0.00'))
        inst = _fake(pk=1, estoque_processado=False, status='RECEBIDO',
                     numero='PED-Z')
        inst.itens.select_related.return_value.all.return_value = [item]
        inst.contrato.filial = _fake()
        inst.recebedor_id = 1
        inst.solicitante_id = 2

        pedido_recebido_gerar_entrada_estoque(sender=None, instance=inst)
        # mesmo com erro, marca processado
        assert inst.estoque_processado is True


# ═══════════════════════════════════════════════
# _entrada_epi
# ═══════════════════════════════════════════════
class TestEntradaEpi:

    def test_sem_equipamento_nao_cria(self):
        material = _fake(equipamento_epi=None, descricao='Capacete', codigo='C1')
        item = _fake(quantidade=2, valor_unitario=Decimal('10'))
        mov_mod = MagicMock()
        with patch.dict('sys.modules',
                        {'seguranca_trabalho.models': mov_mod}):
            _entrada_epi(item, material, _fake(), _fake(numero='P'), 1)
        mov_mod.MovimentacaoEstoque.objects.create.assert_not_called()

    def test_com_equipamento_cria_movimentacao(self):
        equip = _fake(nome='Capacete', pk=3)
        material = _fake(equipamento_epi=equip)
        item = _fake(quantidade=2, valor_unitario=Decimal('10'))
        mov_mod = MagicMock()
        with patch.dict('sys.modules',
                        {'seguranca_trabalho.models': mov_mod}):
            _entrada_epi(item, material, _fake(), _fake(numero='P'), 1)
        mov_mod.MovimentacaoEstoque.objects.create.assert_called_once()


# ═══════════════════════════════════════════════
# _entrada_consumo
# ═══════════════════════════════════════════════
class TestEntradaConsumo:

    @patch('suprimentos.signals.EstoqueConsumo')
    def test_cria_estoque_consumo(self, mock_ec):
        material = _fake(descricao='Cimento')
        item = _fake(quantidade=5)
        pedido = _fake(numero='P', contrato=_fake(cm='CM-1'))
        _entrada_consumo(item, material, _fake(), pedido, 1)
        mock_ec.objects.create.assert_called_once()


# ═══════════════════════════════════════════════
# _entrada_ferramenta
# ═══════════════════════════════════════════════
class TestEntradaFerramenta:

    def test_sem_ferramenta_nao_atualiza(self):
        material = _fake(ferramenta_ref=None, descricao='Furadeira', codigo='F1')
        item = _fake(quantidade=1)
        ferr_mod = MagicMock()
        with patch.dict('sys.modules', {'ferramentas.models': ferr_mod}):
            _entrada_ferramenta(item, material, _fake(), _fake(numero='P'))
        ferr_mod.Ferramenta.objects.filter.assert_not_called()

    def test_com_ferramenta_incrementa(self):
        ferramenta = _fake(nome='Furadeira', pk=8)
        material = _fake(ferramenta_ref=ferramenta)
        item = _fake(quantidade=3)
        ferr_mod = MagicMock()
        with patch.dict('sys.modules', {'ferramentas.models': ferr_mod}):
            _entrada_ferramenta(item, material, _fake(), _fake(numero='P'))
        ferr_mod.Ferramenta.objects.filter.assert_called_once_with(pk=8)
        ferr_mod.Ferramenta.objects.filter.return_value.update \
            .assert_called_once()


# pytest suprimentos/tests/test_signals.py --cov=suprimentos.signals --cov-report=term-missing -v

