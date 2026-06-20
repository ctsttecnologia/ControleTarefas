
"""
Suíte de testes de permissões + fluxo dos views de suprimentos.

Matriz testada:
  - Usuário SEM permissão  → 403 (raise_exception=True)
  - Usuário COM permissão  → 200 ou 302 (sucesso)
  - Usuário ANÔNIMO        → 302 redirect p/ login
"""
import pytest
from django.urls import reverse
from django.contrib.auth.models import Permission

from suprimentos.models import (
    PedidoCompra,
    SolicitacaoCompra,
    ItemSolicitacao,
)

pytestmark = pytest.mark.django_db


# ──────────────────────────────────────────────────────────────
# Helpers de cliente autenticado
# ──────────────────────────────────────────────────────────────
def _login(client, user):
    client.force_login(user)
    return client


def _dar_permissao(user, codename):
    """Concede uma permission pelo codename (app suprimentos)."""
    perm = Permission.objects.get(
        codename=codename,
        content_type__app_label="suprimentos",
    )
    user.user_permissions.add(perm)
    # limpa cache de permissões do request seguinte
    user = type(user).objects.get(pk=user.pk)
    return user


# ══════════════════════════════════════════════════════════════
# MATRIZ DE VIEWS
#   (url_name, method, kwargs_builder, codename_exigido, post_data_builder)
# ══════════════════════════════════════════════════════════════
def _kw_pc(ctx):
    return {"pk": ctx["pedido_compra"].pk}

def _kw_sol(ctx):
    return {"pk": ctx["solicitacao"].pk}


MATRIZ = [
    # view                       método   kwargs    permissão                         dados POST
    ("pc_finalizar",             "post",  _kw_pc,   "pode_receber_pedido_compra",     lambda c: {}),
    ("pc_enviar_fornecedor",     "get",   _kw_pc,   "pode_emitir_pedido_compra",  None),
    ("montar_pedido_compra",     "get",   _kw_sol,  "pode_montar_pc",                 None),
]


# ──────────────────────────────────────────────────────────────
# 1) ANÔNIMO → redireciona para login (302)
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("view_name,method,kw_builder,codename,post_builder", MATRIZ)
def test_view_anonimo_redireciona_login(
    client, view_name, method, kw_builder, codename, post_builder,
    contexto_fluxo,
):
    ctx = contexto_fluxo
    url = reverse(f"suprimentos:{view_name}", kwargs=kw_builder(ctx))

    if method == "post":
        resp = client.post(url, data=(post_builder(ctx) if post_builder else {}))
    else:
        resp = client.get(url)

    assert resp.status_code == 302
    assert "/login" in resp.url.lower() or "/accounts/login" in resp.url.lower()


# ──────────────────────────────────────────────────────────────
# 2) AUTENTICADO SEM permissão → 403
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("view_name,method,kw_builder,codename,post_builder", MATRIZ)
def test_view_sem_permissao_403(
    client, view_name, method, kw_builder, codename, post_builder,
    usuario, contexto_fluxo,
):
    ctx = contexto_fluxo
    _login(client, usuario)  # usuário SEM permissões
    url = reverse(f"suprimentos:{view_name}", kwargs=kw_builder(ctx))

    if method == "post":
        resp = client.post(url, data=(post_builder(ctx) if post_builder else {}))
    else:
        resp = client.get(url)

    assert resp.status_code == 403


# ──────────────────────────────────────────────────────────────
# 3) AUTENTICADO COM permissão → sucesso (200/302)
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("view_name,method,kw_builder,codename,post_builder", MATRIZ)
def test_view_com_permissao_sucesso(
    client, view_name, method, kw_builder, codename, post_builder,
    usuario, contexto_fluxo,
):
    ctx = contexto_fluxo
    usuario = _dar_permissao(usuario, codename)
    _login(client, usuario)
    url = reverse(f"suprimentos:{view_name}", kwargs=kw_builder(ctx))

    if method == "post":
        resp = client.post(url, data=(post_builder(ctx) if post_builder else {}))
    else:
        resp = client.get(url)

    assert resp.status_code in (200, 302), (
        f"{view_name} retornou {resp.status_code} para usuário COM permissão"
    )


# ══════════════════════════════════════════════════════════════
# TESTES DE FLUXO ESPECÍFICOS (lógica de negócio)
# ══════════════════════════════════════════════════════════════

class TestPcFinalizar:
    def test_finalizar_marca_pc_recebido(self, client, usuario, contexto_fluxo):
        ctx = contexto_fluxo
        usuario = _dar_permissao(usuario, "pode_receber_pedido_compra")
        _login(client, usuario)

        pc = ctx["pedido_compra"]
        url = reverse("suprimentos:pc_finalizar", kwargs={"pk": pc.pk})
        resp = client.post(url)

        assert resp.status_code == 302
        pc.refresh_from_db()
        assert pc.status == PedidoCompra.StatusPC.RECEBIDO
        assert pc.recebido_por == usuario
        assert pc.data_entrega_efetiva is not None

    def test_finalizar_completa_quantidade_recebida(self, client, usuario, contexto_fluxo):
        ctx = contexto_fluxo
        usuario = _dar_permissao(usuario, "pode_receber_pedido_compra")
        _login(client, usuario)

        pc = ctx["pedido_compra"]
        url = reverse("suprimentos:pc_finalizar", kwargs={"pk": pc.pk})
        client.post(url)

        for item in pc.itens.all():
            assert item.quantidade_recebida == item.quantidade

    def test_finalizar_unico_pc_conclui_solicitacao(self, client, usuario, contexto_fluxo):
        """
        Se este é o único PC da SOL e ele foi recebido,
        a solicitação deve ir para FINALIZADO.
        ⚠️ Só passa APÓS corrigir CONCLUIDO → FINALIZADO no view.
        """
        ctx = contexto_fluxo
        usuario = _dar_permissao(usuario, "pode_receber_pedido_compra")
        _login(client, usuario)

        url = reverse("suprimentos:pc_finalizar", kwargs={"pk": ctx["pedido_compra"].pk})
        client.post(url)

        sol = ctx["solicitacao"]
        sol.refresh_from_db()
        assert sol.status == SolicitacaoCompra.StatusChoices.FINALIZADO


class TestPcEnviarFornecedor:
    def test_enviar_marca_status_e_data(self, client, usuario, contexto_fluxo):
        ctx = contexto_fluxo
        usuario = _dar_permissao(usuario, "pode_emitir_pedido_compra")
        _login(client, usuario)

        pc = ctx["pedido_compra"]
        url = reverse("suprimentos:pc_enviar_fornecedor", kwargs={"pk": pc.pk})
        resp = client.get(url)

        assert resp.status_code == 302
        pc.refresh_from_db()
        assert pc.status == PedidoCompra.StatusPC.ENVIADO_FORNECEDOR
        assert pc.data_envio is not None


class TestMontarPedidoCompra:
    def test_preview_get_lista_grupos(self, client, usuario, contexto_pre_pc):
        ctx = contexto_pre_pc
        usuario = _dar_permissao(usuario, "pode_montar_pc")
        _login(client, usuario)

        url = reverse("suprimentos:montar_pedido_compra", kwargs={"pk": ctx["solicitacao"].pk})
        resp = client.get(url)

        assert resp.status_code == 200
        assert "grupos_fornecedor" in resp.context

    def test_post_gera_pedido_compra(self, client, usuario, contexto_pre_pc):
        ctx = contexto_pre_pc
        usuario = _dar_permissao(usuario, "pode_montar_pc")
        _login(client, usuario)

        url = reverse("suprimentos:montar_pedido_compra", kwargs={"pk": ctx["solicitacao"].pk})
        resp = client.post(url, data={
            "fornecedores": [str(ctx["fornecedor"].pk)],
            "observacoes": "Teste automatizado",
        })

        assert resp.status_code == 302
        sol = ctx["solicitacao"]
        sol.refresh_from_db()
        assert sol.status == SolicitacaoCompra.StatusChoices.PEDIDO_GERADO
        assert sol.pedidos_compra.count() == 1

    def test_post_idempotente_nao_duplica(self, client, usuario, contexto_pre_pc):
        """Segundo POST não deve gerar PC duplicado."""
        ctx = contexto_pre_pc
        usuario = _dar_permissao(usuario, "pode_montar_pc")
        _login(client, usuario)

        url = reverse("suprimentos:montar_pedido_compra", kwargs={"pk": ctx["solicitacao"].pk})
        data = {"fornecedores": [str(ctx["fornecedor"].pk)], "observacoes": ""}

        client.post(url, data=data)   # 1º → gera
        client.post(url, data=data)   # 2º → idempotente

        ctx["solicitacao"].refresh_from_db()
        assert ctx["solicitacao"].pedidos_compra.count() == 1
