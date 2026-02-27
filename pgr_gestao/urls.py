
"""
URLs para o módulo PGR - Integrado ao projeto existente
"""
from django.urls import path
from . import views

app_name = 'pgr_gestao'

urlpatterns = [

    # ========================================
    # DASHBOARD
    # ========================================
    path('', views.dashboard_gerencial_view, name='dashboard'),

    # ========================================
    # EMPRESAS
    # ========================================
    path('empresas/', views.EmpresaListView.as_view(), name='empresa_list'),
    path('empresas/nova/', views.EmpresaCreateView.as_view(), name='empresa_create'),
    path('empresas/<int:pk>/', views.EmpresaDetailView.as_view(), name='empresa_detail'),
    path('empresas/<int:pk>/editar/', views.EmpresaUpdateView.as_view(), name='empresa_update'),
    path('empresas/<int:pk>/excluir/', views.EmpresaDeleteView.as_view(), name='empresa_delete'),

    # ========================================
    # LOCAIS DE PRESTAÇÃO
    # ========================================
    path('locais/novo/', views.LocalPrestacaoCreateView.as_view(), name='local_prestacao_create'),
    path('locais/<int:pk>/editar/', views.LocalPrestacaoUpdateView.as_view(), name='local_prestacao_update'),

    # ========================================
    # DOCUMENTOS PGR
    # ========================================
    path('documentos/', views.PGRDocumentoListView.as_view(), name='documento_list'),
    path('documentos/novo/', views.PGRDocumentoCreateView.as_view(), name='documento_create'),
    path('documentos/<int:pk>/', views.PGRDocumentoDetailView.as_view(), name='documento_detail'),
    path('documentos/<int:pk>/editar/', views.PGRDocumentoUpdateView.as_view(), name='documento_update'),
    path('documentos/<int:pk>/excluir/', views.PGRDocumentoDeleteView.as_view(), name='documento_delete'),

    # Autocomplete
    path('cliente-autocomplete/', views.ClienteAutocomplete.as_view(), name='cliente-autocomplete'),

    # ========================================
    # REVISÕES
    # ========================================
    path('documentos/<int:pgr_id>/revisoes/nova/', views.PGRRevisaoCreateView.as_view(), name='revisao_create'),
    path('revisoes/<int:pk>/', views.PGRRevisaoDetailView.as_view(), name='revisao_detail'),

    # ========================================
    # PROFISSIONAIS RESPONSÁVEIS
    # ========================================
    path('profissionais/', views.ProfissionalResponsavelListView.as_view(), name='profissional_list'),
    path('profissionais/novo/', views.ProfissionalResponsavelCreateView.as_view(), name='profissional_create'),
    path('profissionais/<int:pk>/editar/', views.ProfissionalResponsavelUpdateView.as_view(), name='profissional_update'),
    path('profissionais/<int:pk>/excluir/', views.ProfissionalResponsavelDeleteView.as_view(), name='profissional_delete'),

    # ========================================
    # GES - Grupos de Exposição Similar
    # ========================================
    path('ges/', views.GESListView.as_view(), name='ges_list'),
    path('ges/novo/', views.GESCreateView.as_view(), name='ges_create'),
    path('ges/<int:pk>/', views.GESDetailView.as_view(), name='ges_detail'),
    path('ges/<int:pk>/editar/', views.GESUpdateView.as_view(), name='ges_update'),
    path('ges/<int:pk>/excluir/', views.GESDeleteView.as_view(), name='ges_delete'),
    path('ges/<int:pk>/toggle-ativo/', views.ges_toggle_ativo, name='ges_toggle_ativo'),

    # ========================================
    # RISCOS IDENTIFICADOS
    # ========================================
    path('riscos/', views.RiscoIdentificadoListView.as_view(), name='risco_list'),
    path('riscos/novo/', views.RiscoIdentificadoCreateView.as_view(), name='risco_create'),
    path('riscos/<int:pk>/', views.RiscoIdentificadoDetailView.as_view(), name='risco_detail'),
    path('riscos/<int:pk>/editar/', views.RiscoIdentificadoUpdateView.as_view(), name='risco_update'),
    path('riscos/<int:pk>/excluir/', views.RiscoIdentificadoDeleteView.as_view(), name='risco_delete'),

    # ========================================
    # AVALIAÇÕES QUANTITATIVAS
    # ========================================
    path('avaliacoes/', views.AvaliacaoQuantitativaListView.as_view(), name='avaliacao_list'),
    path('avaliacoes/nova/', views.AvaliacaoQuantitativaCreateView.as_view(), name='avaliacao_create'),
    path('avaliacoes/<int:pk>/', views.AvaliacaoQuantitativaDetailView.as_view(), name='avaliacao_detail'),
    path('avaliacoes/<int:pk>/editar/', views.AvaliacaoQuantitativaUpdateView.as_view(), name='avaliacao_update'),
    path('avaliacoes/<int:pk>/excluir/', views.AvaliacaoQuantitativaDeleteView.as_view(), name='avaliacao_delete'),
    # Criar avaliação a partir de um risco específico
    path('riscos/<int:risco_id>/avaliacoes/nova/', views.AvaliacaoQuantitativaCreateView.as_view(), name='avaliacao_create_risco'),

    # ========================================
    # PLANOS DE AÇÃO
    # ========================================
    path('planos-acao/', views.PlanoAcaoPGRListView.as_view(), name='plano_acao_list'),
    path('planos-acao/novo/', views.PlanoAcaoPGRCreateView.as_view(), name='plano_acao_create'),
    path('planos-acao/<int:pk>/', views.PlanoAcaoPGRDetailView.as_view(), name='plano_acao_detail'),
    path('planos-acao/<int:pk>/editar/', views.PlanoAcaoPGRUpdateView.as_view(), name='plano_acao_update'),
    path('planos-acao/<int:pk>/concluir/', views.concluir_plano_acao, name='plano_acao_concluir'),
    path('planos-acao/<int:pk>/anexo/', views.adicionar_anexo_plano, name='adicionar_anexo_plano'),

    # ========================================
    # CRONOGRAMA DE AÇÕES
    # ========================================

    # Listagem geral
    path('cronograma/', views.CronogramaAcaoListView.as_view(), name='cronograma_list'),

    # CRUD geral (sem pgr_pk — usado a partir da listagem)
    path('cronograma/novo/', views.CronogramaAcaoCreateView.as_view(), name='cronograma_create_geral'),
    path('cronograma/<int:pk>/', views.CronogramaAcaoDetailView.as_view(), name='cronograma_detail'),
    path('cronograma/<int:pk>/editar/', views.CronogramaAcaoUpdateView.as_view(), name='cronograma_update'),
    path('cronograma/<int:pk>/excluir/', views.CronogramaAcaoDeleteView.as_view(), name='cronograma_delete'),
    path('cronograma/<int:pk>/status/', views.atualizar_status_acao, name='atualizar_status_acao'),

    # CRUD vinculado a um documento PGR específico
    path('documentos/<int:pgr_pk>/cronograma/novo/', views.CronogramaAcaoCreateView.as_view(), name='cronograma_create'),
    path('documentos/<int:pgr_pk>/cronograma/<int:pk>/editar/', views.CronogramaAcaoUpdateView.as_view(), name='cronograma_update_pgr'),
    path('documentos/<int:pgr_pk>/cronograma/<int:pk>/excluir/', views.CronogramaAcaoDeleteView.as_view(), name='cronograma_delete_pgr'),

    # ========================================
    # RELATÓRIOS (unificado)
    # ========================================
    path('relatorios/', views.relatorios_pgr, name='relatorios'),
    path('relatorios/riscos-classificacao/', views.relatorio_riscos_por_classificacao, name='relatorio_riscos_classificacao'),
    path('relatorios/planos-acao/', views.relatorio_planos_acao, name='relatorio_planos_acao'),
    #path('relatorios/ges/', views.relatorio_ges, name='relatorio_ges'),

    # ========================================
    # EXPORTAÇÕES
    # ========================================
    path('documentos/<int:pk>/pdf/', views.gerar_relatorio_completo_pdf, name='relatorio_completo_pdf'),
    path('documentos/<int:pk>/excel/', views.exportar_inventario_riscos_excel, name='exportar_inventario_excel'),
    path('documentos/<int:pk>/cronograma-excel/', views.exportar_cronograma_acoes, name='exportar_cronograma_acoes'),
    #path('documentos/<int:pk>/cronograma-excel-v2/', views.exportar_cronograma_excel, name='exportar_cronograma_excel'),
    path('documentos/<int:pk>/verificar-conformidade/', views.verificar_conformidade_pgr, name='verificar_conformidade'),
    path('exportar/planos-de-acao/', views.exportar_planos_acao_excel, name='exportar_planos_acao_excel'),

    # ========================================
    # AJAX / API ENDPOINTS
    # ========================================
    path('ajax/locais-prestacao/<int:empresa_id>/', views.get_locais_prestacao_ajax, name='ajax_locais_prestacao'),
    path('ajax/locais/<int:empresa_id>/', views.load_locais_prestacao, name='ajax_load_locais'),
    path('ajax/ges/<int:pgr_id>/', views.get_ges_ajax, name='ajax_ges'),
    path('ajax/dashboard-stats/', views.dashboard_stats_ajax, name='ajax_dashboard_stats'),

]


