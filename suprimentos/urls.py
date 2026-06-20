
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
    path("pedidos-compra/<int:pk>/enviar/", views.pc_enviar_fornecedor, name="pc_enviar_fornecedor"),
    path("pedidos-compra/<int:pk>/entrega/", views.pc_acompanhar_entrega, name="pc_acompanhar_entrega"),
    path("pedidos-compra/<int:pk>/finalizar/", views.pc_finalizar, name="pc_finalizar"),
    path("pedidos-compra/<int:pk>/", views.pc_detalhe, name="pc_detalhe"),
    path("pedidos-compra/", views.PedidoCompraListView.as_view(), name="pc_list",),
    path("pedidos/<int:pk>/anexos/upload/", views.AnexoPedidoUploadView.as_view(), name="pedido_anexo_upload",),

    path("pedidos-compra/<int:pk>/imprimir/", views.PedidoCompraImprimirView.as_view(), name="pedido_compra_imprimir"),

    # ── Cadastros auxiliares ───────────────────────────────
    path("parceiros/", views.ParceiroListView.as_view(), name="parceiro_list"),
    path("parceiros/novo/", views.ParceiroCreateView.as_view(), name="parceiro_novo"),
    path("parceiros/", views.ParceiroListView.as_view(), name="parceiro_list"),
    path("parceiros/novo/", views.ParceiroCreateView.as_view(), name="parceiro_create"),
    path("parceiros/<int:pk>/", views.ParceiroDetailView.as_view(), name="parceiro_detail"),
    path("parceiros/<int:pk>/editar/", views.ParceiroUpdateView.as_view(), name="parceiro_update"),
    path("parceiros/importar/", views.ParceiroUploadMassaView.as_view(), name="parceiro_upload_massa"),
    path("parceiros/importar/modelo/", views.ParceiroModeloDownloadView.as_view(), name="parceiro_modelo_download"),

    path("materiais/novo/", views.MaterialCreateView.as_view(), name="material_novo"),
    path("materiais/", views.MaterialListView.as_view(), name="material_list"),
    path("materiais/novo/", views.MaterialCreateView.as_view(), name="material_create"),
    path("materiais/<int:pk>/", views.MaterialDetailView.as_view(), name="material_detail"),
    path("materiais/<int:pk>/editar/", views.MaterialUpdateView.as_view(), name="material_update"),
    path("materiais/<int:pk>/excluir/", views.MaterialDeleteView.as_view(), name="material_delete"),

    # ── Lançamento em massa ────────────────────────────────────────
    path("materiais/importar/", views.MaterialUploadMassaView.as_view(), name="material_upload_massa"),
    path("materiais/modelo/download/", views.MaterialModeloDownloadView.as_view(), name="material_modelo_download"),

    path("contratos/", views.ContratoListView.as_view(), name="contrato_list"),
    path("contratos/novo/", views.ContratoCreateView.as_view(), name="contrato_criar"),
    path("contratos/<int:pk>/", views.ContratoDetailView.as_view(), name="contrato_detalhe"),
    path("contratos/<int:pk>/editar/", views.ContratoUpdateView.as_view(), name="contrato_editar"),
    path("contratos/<int:pk>/excluir/", views.ContratoDeleteView.as_view(), name="contrato_excluir"),

    # ── Verbas Mensais ──────────────────────────────────────
    path("verbas/", views.VerbaContratoListView.as_view(), name="verba_list"),
    path("verbas/nova/", views.VerbaContratoCreateView.as_view(), name="verba_create"),
    path("verbas/<int:pk>/", views.VerbaContratoDetailView.as_view(), name="verba_detail"),
    path("verbas/<int:pk>/editar/", views.VerbaContratoUpdateView.as_view(), name="verba_update"),
    path("verbas/<int:pk>/excluir/", views.VerbaContratoDeleteView.as_view(), name="verba_delete"),
    
]
