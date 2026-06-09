
# suprimentos/urls.py
from django.urls import path
from . import views

app_name = "suprimentos"

urlpatterns = [
    # Dashboard
    path("", views.SuprimentosDashboard.as_view(), name="dashboard"),

    # ── 1. Pedido ──────────────────────────────────────────
    path("pedidos/", views.PedidoListView.as_view(), name="pedido_list"),
    path("pedidos/novo/", views.PedidoCreateView.as_view(), name="pedido_novo"),
    path("pedidos/<int:pk>/", views.PedidoDetailView.as_view(), name="pedido_detalhe"),
    path("pedidos/<int:pk>/editar/", views.PedidoUpdateView.as_view(), name="pedido_editar"),
    path("pedidos/<int:pk>/submeter/", views.pedido_submeter, name="pedido_submeter"),

    # ── 2. Aprovar Pedido ──────────────────────────────────
    path("pedidos/<int:pk>/aprovar/", views.pedido_aprovar, name="pedido_aprovar"),

    # ── 3. Solicitação / Cotação (NxN) ─────────────────────
    path("solicitacoes/", views.SolicitacaoListView.as_view(), name="solicitacao_list"),
    path("solicitacoes/<int:pk>/", views.SolicitacaoDetailView.as_view(), name="solicitacao_detalhe"),
    path("cotacoes/<int:pk>/excluir/", views.cotacao_excluir, name="cotacao_excluir"),
    path("solicitacoes/<int:pk>/enviar-aprovacao/", views.solicitacao_enviar_aprovacao, name="solicitacao_enviar_aprovacao"),
    path("solicitacao/<int:solicitacao_pk>/cotacao/adicionar/", views.cotacao_adicionar, name="cotacao_adicionar"),

    # ── 4. Aprovar Cotação ─────────────────────────────────
    path("solicitacoes/<int:pk>/aprovar-cotacao/", views.cotacao_aprovar, name="cotacao_aprovar"),

    # ── 5. Montar Pedido de Compra ─────────────────────────
    path("solicitacoes/<int:pk>/montar-pc/", views.montar_pedido_compra, name="montar_pedido_compra"),

    # ── 6. Pedido de Compra / Entrega / Finalizar ──────────
    path("pedidos-compra/<int:pk>/", views.PedidoCompraDetailView.as_view(), name="pedido_compra_detalhe"),
    path("pedidos-compra/<int:pk>/enviar/", views.pc_enviar_fornecedor, name="pc_enviar_fornecedor"),
    path("pedidos-compra/<int:pk>/entrega/", views.pc_acompanhar_entrega, name="pc_acompanhar_entrega"),
    path("pedidos-compra/<int:pk>/finalizar/", views.pc_finalizar, name="pc_finalizar"),
    path("pedidos-compra/<int:pk>/entrega/", views.pc_acompanhar_entrega,name="pc_entrega",),
    path("pedidos-compra/<int:pk>/", views.pc_detalhe, name="pc_detalhe"),

    # ── Cadastros auxiliares ───────────────────────────────
    path("parceiros/", views.ParceiroListView.as_view(), name="parceiro_list"),
    path("parceiros/novo/", views.ParceiroCreateView.as_view(), name="parceiro_novo"),
    path("materiais/", views.MaterialListView.as_view(), name="material_list"),
    path("materiais/novo/", views.MaterialCreateView.as_view(), name="material_novo"),
    path("contratos/", views.ContratoListView.as_view(), name="contrato_list"),
    path("pedidos-compra/<int:pk>/imprimir/", views.PedidoCompraImprimirView.as_view(), name="pedido_compra_imprimir"),
]
