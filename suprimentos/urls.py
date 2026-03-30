
from django.urls import path
from . import views

app_name = 'suprimentos'

urlpatterns = [
    # ── Parceiros ──────────────────────────
    path('parceiros/', views.ParceiroListView.as_view(), name='parceiro_list'),
    path('parceiros/novo/', views.ParceiroCreateView.as_view(), name='parceiro_create'),
    path('parceiros/<int:pk>/', views.ParceiroDetailView.as_view(), name='parceiro_detail'),
    path('parceiros/<int:pk>/editar/', views.ParceiroUpdateView.as_view(), name='parceiro_update'),
    path('parceiros/<int:pk>/deletar/', views.ParceiroDeleteView.as_view(), name='parceiro_delete'),
    path('parceiros/upload/', views.ParceiroBulkUploadView.as_view(), name='parceiro_upload_massa'),
    path('parceiros/upload/template/', views.parceiro_download_template, name='parceiro_download_template'),
    path('parceiros/upload/erros/', views.parceiro_download_erros, name='parceiro_download_erros'),

    # ── Dashboard ──────────────────────────
    path('', views.DashboardSuprimentosView.as_view(), name='dashboard'),

    # ── Catálogo de Materiais ──────────────
    path('materiais/', views.MaterialListView.as_view(), name='material_lista'),
    path('materiais/novo/', views.MaterialCreateView.as_view(), name='material_criar'),
    path('materiais/<int:pk>/editar/', views.MaterialUpdateView.as_view(), name='material_editar'),

    # ── Contratos ──────────────────────────
    path('contratos/', views.ContratoListView.as_view(), name='contrato_lista'),
    path('contratos/novo/', views.ContratoCreateView.as_view(), name='contrato_criar'),
    path('contratos/<int:pk>/', views.ContratoDetailView.as_view(), name='contrato_detalhe'),
    path('contratos/<int:pk>/editar/', views.ContratoUpdateView.as_view(), name='contrato_editar'),

    # ── Pedidos (Solicitante → Gerente) ────
    path('pedidos/', views.PedidoListView.as_view(), name='pedido_lista'),
    path('pedidos/novo/', views.PedidoCreateView.as_view(), name='pedido_criar'),
    path('pedidos/<int:pk>/', views.PedidoDetailView.as_view(), name='pedido_detalhe'),
    path('pedidos/<int:pk>/item/adicionar/', views.ItemPedidoCreateView.as_view(), name='item_adicionar'),
    path('pedidos/<int:pk>/item/<int:item_pk>/remover/', views.ItemPedidoDeleteView.as_view(), name='item_remover'),
    path('pedidos/<int:pk>/enviar/', views.PedidoEnviarView.as_view(), name='pedido_enviar'),
    path('pedidos/<int:pk>/aprovar/', views.PedidoAprovarView.as_view(), name='pedido_aprovar'),
    path('pedidos/<int:pk>/reprovar/', views.PedidoReprovarView.as_view(), name='pedido_reprovar'),
    path('pedidos/<int:pk>/devolver/', views.PedidoDevolverView.as_view(), name='pedido_devolver'),
    path('pedidos/<int:pk>/revisar/', views.PedidoRevisarView.as_view(), name='pedido_revisar'),
    path('pedidos/<int:pk>/entregar/', views.PedidoEntregarView.as_view(), name='pedido_entregar'),
    path('pedidos/<int:pk>/receber/', views.PedidoReceberView.as_view(), name='pedido_receber'),
    path('pedidos/<int:pk>/anexo/', views.PedidoAnexoView.as_view(), name='pedido_anexo'),
    path('pedidos/<int:pk>/anexo/<int:anexo_pk>/remover/', views.PedidoAnexoDeleteView.as_view(), name='pedido_anexo_remover'),

    # ── Solicitações de Compra (pós-aprovação) ──
    path('solicitacoes/', views.SolicitacaoListView.as_view(), name='solicitacao_lista'),
    path('solicitacoes/<int:pk>/', views.SolicitacaoDetailView.as_view(), name='solicitacao_detalhe'),
    path('solicitacoes/<int:pk>/cotacao/', views.SolicitacaoCotacaoView.as_view(), name='solicitacao_cotacao'),
    path('solicitacoes/<int:pk>/validar-cotacao/', views.SolicitacaoValidarCotacaoView.as_view(), name='solicitacao_validar_cotacao'),
    path('solicitacoes/<int:pk>/criar-pedido/', views.SolicitacaoCriarPedidoView.as_view(), name='solicitacao_criar_pedido'),
    path('solicitacoes/<int:pk>/aprovar-pedido/', views.SolicitacaoAprovarPedidoView.as_view(), name='solicitacao_aprovar_pedido'),
    path('solicitacoes/<int:pk>/enviar-fornecedor/', views.SolicitacaoEnviarFornecedorView.as_view(), name='solicitacao_enviar_fornecedor'),
    path('solicitacoes/<int:pk>/registrar-entrega/', views.SolicitacaoRegistrarEntregaView.as_view(), name='solicitacao_registrar_entrega'),
    path('solicitacoes/<int:pk>/encerrar/', views.SolicitacaoEncerrarView.as_view(), name='solicitacao_encerrar'),
    path('solicitacoes/<int:pk>/cancelar/', views.SolicitacaoCancelarView.as_view(), name='solicitacao_cancelar'),
    path('solicitacoes/<int:pk>/anexo/', views.SolicitacaoAnexoView.as_view(), name='solicitacao_anexo'),
    path('solicitacoes/<int:pk>/anexo/<int:anexo_pk>/remover/', views.SolicitacaoAnexoDeleteView.as_view(), name='solicitacao_anexo_remover'),
    path('solicitacoes/<int:pk>/observacao/', views.SolicitacaoObservacaoView.as_view(), name='solicitacao_observacao'),

    # ── Relatórios Gerenciais ──────────────
    path('relatorios/', views.RelatorioSuprimentosView.as_view(), name='relatorio'),
    path('relatorios/pdf/', views.RelatorioPDFView.as_view(), name='relatorio_pdf'),
    path('relatorios/excel/', views.RelatorioExcelView.as_view(), name='relatorio_excel'),

    # ── API interna (AJAX) ─────────────────
    path('api/material/<int:pk>/preco/', views.material_preco_api, name='material_preco'),
    path('api/contrato/<int:pk>/saldos/', views.contrato_saldos_api, name='contrato_saldos'),
]


