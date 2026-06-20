
# suprimentos/tests/conftest.py

import pytest
from decimal import Decimal
from datetime import date, datetime, time
from django.utils import timezone
from django.contrib.auth.models import Permission
from suprimentos.models import Cotacao, ItemSolicitacao, PedidoCompra


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _aware(valor):
    """
    Normaliza date/datetime para datetime AWARE no timezone ativo.
    Evita RuntimeWarning de naive datetime ao salvar em DateTimeField.
    """
    if isinstance(valor, datetime):
        dt = valor
    elif isinstance(valor, date):
        dt = datetime.combine(valor, time.min)
    else:
        return valor
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


# ═══════════════════════════════════════════════════════════════
# USUÁRIOS
# ═══════════════════════════════════════════════════════════════

@pytest.fixture   # ← ESTAVA FALTANDO
def usuario(db, django_user_model):
    """Usuário padrão (solicitante/aprovador), SEM permissões custom."""
    return django_user_model.objects.create_user(
        username="tester",
        email="tester@example.com",
        password="x123456!",
    )

# Todas as permissões custom REAIS declaradas nos models do app.
PERMISSOES_SUPRIMENTOS = [
    # Pedido
    "pode_aprovar_pedido",
    # SolicitacaoCompra
    "pode_executar_cotacao",
    "pode_montar_pc",
    "pode_enviar_pc",
    "pode_aprovar_pc",
    "pode_entregar_pc",
    "pode_concluir_pc",
    "pode_cancelar_pc",
    # Cotacao
    "pode_cotar",
    "pode_aprovar_cotacao",
    # PedidoCompra
    "pode_emitir_pedido_compra",
    "pode_receber_pedido_compra",
    "pode_cancelar_pedido_compra",
    "pode_visualizar_pedido_compra",
    # AnexoPedido
    "view_anexopedido_outros",
    "download_anexopedido",
    # AnexoSolicitacao
    "view_anexosolicitacao_confidencial",
    "download_anexosolicitacao",
]


@pytest.fixture
def usuario_com_permissoes(db, django_user_model):
    """
    Usuário com TODAS as permissões custom REAIS do app suprimentos.

    ⚠️ Os views usam 'pode_receber_pc' e 'pode_visualizar_pc', que NÃO
    existem em nenhum model. Para esses views funcionarem em teste,
    corrija os views OU adicione esses codenames nos Meta.permissions.
    """
    user = django_user_model.objects.create_user(
        username="gerente",
        email="permitido@example.com",   # ← ESSENCIAL
        password="x123456!",
    )

    perms = Permission.objects.filter(
        content_type__app_label="suprimentos",
        codename__in=PERMISSOES_SUPRIMENTOS,
    )

    encontradas = set(perms.values_list("codename", flat=True))
    faltando = set(PERMISSOES_SUPRIMENTOS) - encontradas
    assert not faltando, (
        f"Permissões não encontradas (rode makemigrations/migrate?): {faltando}"
    )

    user.user_permissions.set(perms)
    # Recarrega para limpar cache de permissões
    return django_user_model.objects.get(pk=user.pk)


@pytest.fixture
def client_gerente(client, usuario_com_permissoes):
    """Client já autenticado com o usuário que tem todas as permissões."""
    client.force_login(usuario_com_permissoes)
    return client


@pytest.fixture
def contexto_fluxo(
    db,
    usuario,
    fornecedor,
    solicitacao,          # já vem com ItemSolicitacao (FAZER_COTACAO)
    cotacao_factory,
):
    """
    Monta o fluxo completo e retorna instâncias REAIS:

        Pedido → SolicitacaoCompra → ItemSolicitacao
               → Cotacao → PedidoCompra → ItemPedidoCompra

    Use no test_views_permissoes.py via:
        ctx["pedido"], ctx["solicitacao"], ctx["cotacao"], ctx["pedido_compra"]
    """
    from suprimentos.models import (
        ItemSolicitacao,
        PedidoCompra,
        ItemPedidoCompra,
        SolicitacaoCompra,
    )

    # 1) Pedido de origem (a solicitação tem OneToOne reverso "pedido")
    pedido = solicitacao.pedido

    # 2) Primeiro ItemSolicitacao gerado automaticamente
    item_solicitacao = solicitacao.itens.first()
    assert item_solicitacao is not None, (
        "A solicitação não gerou ItemSolicitacao. "
        "Verifique gerar_solicitacao_compra(usar_novo_fluxo=True)."
    )

    # 3) Cotação para esse item
    cotacao = cotacao_factory(item_solicitacao, valor_unitario="45.00")

    # 4) Aprova a cotação no item (necessário p/ montar PC)
    item_solicitacao.cotacao_escolhida = cotacao
    item_solicitacao.status = ItemSolicitacao.StatusItem.APROVADO
    item_solicitacao.save(update_fields=["cotacao_escolhida", "status"])

    # 5) Pedido de Compra real
    pedido_compra = PedidoCompra.objects.create(
        solicitacao=solicitacao,
        fornecedor=fornecedor,
        filial=solicitacao.filial,
        criado_por=usuario,
        status=PedidoCompra.StatusPC.EMITIDO,
    )

    # 6) Item do PC (snapshot da cotação) — dispara recalcular_total()
    ItemPedidoCompra.objects.create(
        pedido_compra=pedido_compra,
        cotacao=cotacao,
        item_solicitacao=item_solicitacao,
        material=item_solicitacao.material,
        quantidade=item_solicitacao.quantidade,
        valor_unitario=cotacao.valor_unitario,
    )

    pedido_compra.refresh_from_db()

    return {
        "pedido": pedido,
        "solicitacao": solicitacao,
        "item_solicitacao": item_solicitacao,
        "cotacao": cotacao,
        "pedido_compra": pedido_compra,
    }

@pytest.fixture
def contexto_pre_pc(
    db,
    usuario,
    fornecedor,
    solicitacao,
    cotacao_factory,
):
    """
    Fluxo até o ponto IMEDIATAMENTE ANTES de gerar o Pedido de Compra.
    Estado:
      - Solicitação: FAZER_COTACAO (ainda NÃO virou PEDIDO_GERADO)
      - ItemSolicitacao: APROVADO + cotacao_escolhida definida
      - Nenhum PedidoCompra criado
    Use em testes de `montar_pedido_compra`.
    """
    from suprimentos.models import ItemSolicitacao

    item_solicitacao = solicitacao.itens.first()
    assert item_solicitacao is not None, "Falha ao obter ItemSolicitacao"

    cotacao = cotacao_factory(item_solicitacao, valor_unitario="45.00")

    item_solicitacao.cotacao_escolhida = cotacao
    item_solicitacao.status = ItemSolicitacao.StatusItem.APROVADO
    item_solicitacao.save(update_fields=["cotacao_escolhida", "status"])

    return {
        "pedido": solicitacao.pedido,
        "solicitacao": solicitacao,
        "item_solicitacao": item_solicitacao,
        "cotacao": cotacao,
        "fornecedor": cotacao.fornecedor,
    }


# ═══════════════════════════════════════════════════════════════
# FILIAL / CONTRATO / VERBAS
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def filial(db):
    """Filial mínima. Ajuste campos obrigatórios conforme usuario.models.Filial."""
    from usuario.models import Filial
    return Filial.objects.create(nome="Matriz")


@pytest.fixture
def contrato(db, filial):
    """Contrato ativo vinculado à filial."""
    from suprimentos.models import Contrato
    return Contrato.objects.create(
        cm="0001",
        cliente="Cliente Teste",
        filial=filial,
        ativo=True,
    )


@pytest.fixture
def verba_factory(db):
    """
    Cria/atualiza a VerbaContrato de um mês específico.

    Uso:
        verba_factory(contrato, ano=2026, mes=6,
                      epi="1000", consumo="5000", ferramenta="2000")
    """
    from suprimentos.models import VerbaContrato

    def _make(contrato, ano=None, mes=None,
              epi="0.00", consumo="0.00", ferramenta="0.00"):
        hoje = date.today()
        ano = ano or hoje.year
        mes = mes or hoje.month
        verba, _criada = VerbaContrato.objects.update_or_create(
            contrato=contrato, ano=ano, mes=mes,
            defaults={
                "verba_epi": Decimal(str(epi)),
                "verba_consumo": Decimal(str(consumo)),
                "verba_ferramenta": Decimal(str(ferramenta)),
            },
        )
        return verba

    return _make


@pytest.fixture
def contrato_com_verba(db, contrato, verba_factory):
    """Contrato já com verba farta no mês atual (evita estourar saldo nos testes)."""
    verba_factory(
        contrato,
        epi="10000.00",
        consumo="50000.00",
        ferramenta="20000.00",
    )
    return contrato


# ═══════════════════════════════════════════════════════════════
# MATERIAL
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def material_factory(db, filial):
    """
    Cria Material. `classificacao` controla a verba (CONSUMO/EPI/FERRAMENTA);
    `tipo` é a categoria visual.
    """
    from suprimentos.models import Material

    def _make(descricao="Material Teste", tipo="CIVIL",
              classificacao="CONSUMO", valor_unitario="10.00", **kwargs):
        return Material.objects.create(
            descricao=descricao,
            tipo=tipo,
            classificacao=classificacao,
            valor_unitario=Decimal(str(valor_unitario)),
            filial=filial,
            **kwargs,
        )

    return _make


@pytest.fixture
def material(db, material_factory):
    """Material de consumo pronto pra uso direto."""
    return material_factory()


# ═══════════════════════════════════════════════════════════════
# PARCEIRO / FORNECEDOR
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def fornecedor(db, filial):
    """Parceiro fornecedor ativo (necessário p/ Cotacao e PedidoCompra)."""
    from suprimentos.models import Parceiro
    return Parceiro.objects.create(
        nome_fantasia="Fornecedor Teste",
        razao_social="Fornecedor Teste LTDA",
        cnpj="11.111.111/0001-11",
        eh_fornecedor=True,
        ativo=True,
        filial=filial,
    )


# ═══════════════════════════════════════════════════════════════
# PEDIDO + ITENS
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def pedido_factory(db, usuario):
    """
    Cria um Pedido + 1 ItemPedido.
    ...
    """
    from suprimentos.models import Pedido, ItemPedido

    def _make(contrato, material, data, valor, qtd=1, status="APROVADO"):
        pedido = Pedido.objects.create(
            contrato=contrato,
            filial=contrato.filial,
            status=status,
            solicitante=usuario,
        )

        # data_pedido é auto_now_add -> força via update() com datetime AWARE
        dt = _aware(data)  # ✅ converte date/datetime naive -> aware
        Pedido.objects.filter(pk=pedido.pk).update(data_pedido=dt)
        pedido.refresh_from_db()

        valor_total = Decimal(str(valor))
        qtd_dec = Decimal(str(qtd))
        valor_unitario = (valor_total / qtd_dec).quantize(Decimal("0.01"))

        ItemPedido.objects.create(
            pedido=pedido,
            material=material,
            quantidade=qtd,
            valor_unitario=valor_unitario,
        )
        return pedido

    return _make



# ═══════════════════════════════════════════════════════════════
# SOLICITAÇÃO DE COMPRA + ITENS
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def solicitacao_factory(db, usuario):
    """..."""
    from suprimentos.models import Pedido

    def _make(pedido, usar_novo_fluxo=True, gerar=True):
        if pedido.status != Pedido.StatusChoices.APROVADO:
            pedido.status = Pedido.StatusChoices.APROVADO
            pedido.save(update_fields=["status"])

        if not pedido.aprovador_id:
            pedido.aprovador = usuario
            pedido.data_aprovacao = timezone.now()  # ✅ aware (era date.today())
            pedido.save(update_fields=["aprovador", "data_aprovacao"])

        if gerar:
            return pedido.gerar_solicitacao_compra(
                usuario=usuario, usar_novo_fluxo=usar_novo_fluxo
            )
        return None

    return _make



@pytest.fixture
def solicitacao(db, contrato_com_verba, material, pedido_factory, solicitacao_factory):
    """SolicitacaoCompra pronta, já com ItemSolicitacao, no status FAZER_COTACAO."""
    pedido = pedido_factory(
        contrato=contrato_com_verba,
        material=material,
        data=date.today(),
        valor="100.00",
        qtd=2,
        status="APROVADO",
    )
    return solicitacao_factory(pedido)


# ═══════════════════════════════════════════════════════════════
# COTAÇÃO
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def cotacao_factory(db, usuario, fornecedor):
    """
    Cria uma Cotacao para um ItemSolicitacao.

    Uso:
        cot = cotacao_factory(item_solicitacao, valor_unitario="45.00")
    """
    from suprimentos.models import Cotacao

    def _make(item_solicitacao, valor_unitario="50.00",
              fornecedor_obj=None, prazo_entrega_dias=10):
        return Cotacao.objects.create(
            item_solicitacao=item_solicitacao,
            fornecedor=fornecedor_obj or fornecedor,
            valor_unitario=Decimal(str(valor_unitario)),
            prazo_entrega_dias=prazo_entrega_dias,
            criado_por=usuario,
        )

    return _make



# Rodar o Coverege com: 
# coverage run manage.py test --settings=gerenciandoTarefas.settings_test -v 2
# coverage report
# coverage html