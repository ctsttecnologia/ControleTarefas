from django.urls import path
from . import views
from .views import ajax_cargo_info, ajax_funcao_st_info

app_name = "ltcat"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),

    # ════ EMPRESA LTCAT (Contratada) ════
    path("empresas/", views.EmpresaLTCATListView.as_view(), name="empresa_ltcat_list"),
    path("empresas/nova/", views.EmpresaLTCATCreateView.as_view(), name="empresa_ltcat_create"),
    path("empresas/<int:pk>/editar/", views.EmpresaLTCATUpdateView.as_view(), name="empresa_ltcat_update"),
    path("empresas/<int:pk>/excluir/", views.EmpresaLTCATDeleteView.as_view(), name="empresa_ltcat_delete"),

    # LTCAT CRUD
    path("laudos/", views.LTCATListView.as_view(), name="ltcat_list"),
    path("laudos/novo/", views.LTCATCreateView.as_view(), name="ltcat_create"),
    path("laudos/<int:pk>/", views.LTCATDetailView.as_view(), name="ltcat_detail"),
    path("laudos/<int:pk>/editar/", views.LTCATUpdateView.as_view(), name="ltcat_update"),
    path("laudos/<int:pk>/excluir/", views.LTCATDeleteView.as_view(), name="ltcat_delete"),


    # LOCAIS DE PRESTAÇÃO DE SERVIÇO
    path("locais/", views.LocalPrestacaoListView.as_view(), name="local_list"),
    path("locais/novo/", views.LocalPrestacaoCreateView.as_view(), name="local_create"),
    path("locais/<int:pk>/editar/", views.LocalPrestacaoUpdateView.as_view(), name="local_update"),
    path("locais/<int:pk>/excluir/", views.LocalPrestacaoDeleteView.as_view(), name="local_delete"),

    # Revisões
    path("laudos/<int:ltcat_pk>/revisoes/nova/", views.RevisaoCreateView.as_view(), name="revisao_create"),
    path("laudos/<int:ltcat_pk>/revisoes/<int:pk>/editar/", views.RevisaoUpdateView.as_view(), name="revisao_update"),
    path("laudos/<int:ltcat_pk>/revisoes/<int:pk>/excluir/", views.RevisaoDeleteView.as_view(), name="revisao_delete"),

    # Funções Analisadas
    path("laudos/<int:ltcat_pk>/funcoes/nova/", views.FuncaoCreateView.as_view(), name="funcao_create"),
    path("laudos/<int:ltcat_pk>/funcoes/<int:pk>/editar/", views.FuncaoUpdateView.as_view(), name="funcao_update"),
    path("laudos/<int:ltcat_pk>/funcoes/<int:pk>/excluir/", views.FuncaoDeleteView.as_view(), name="funcao_delete"),

    # Riscos
    path("laudos/<int:ltcat_pk>/riscos/novo/", views.RiscoCreateView.as_view(), name="risco_create"),
    path("laudos/<int:ltcat_pk>/riscos/<int:pk>/editar/", views.RiscoUpdateView.as_view(), name="risco_update"),
    path("laudos/<int:ltcat_pk>/riscos/<int:pk>/excluir/", views.RiscoDeleteView.as_view(), name="risco_delete"),

    # Periculosidade
    path("laudos/<int:ltcat_pk>/periculosidade/nova/", views.PericulosidadeCreateView.as_view(), name="periculosidade_create"),
    path("laudos/<int:ltcat_pk>/periculosidade/<int:pk>/editar/", views.PericulosidadeUpdateView.as_view(), name="periculosidade_update"),

    # Conclusões
    path("laudos/<int:ltcat_pk>/conclusoes/nova/", views.ConclusaoCreateView.as_view(), name="conclusao_create"),
    path("laudos/<int:ltcat_pk>/conclusoes/<int:pk>/editar/", views.ConclusaoUpdateView.as_view(), name="conclusao_update"),

    # Recomendações
    path("laudos/<int:ltcat_pk>/recomendacoes/nova/", views.RecomendacaoCreateView.as_view(), name="recomendacao_create"),
    path("laudos/<int:ltcat_pk>/recomendacoes/<int:pk>/editar/", views.RecomendacaoUpdateView.as_view(), name="recomendacao_update"),
    path("laudos/<int:ltcat_pk>/recomendacoes/<int:pk>/excluir/", views.RecomendacaoDeleteView.as_view(), name="recomendacao_delete"),

    # Anexos
    path("laudos/<int:ltcat_pk>/anexos/novo/", views.AnexoCreateView.as_view(), name="anexo_create"),
    path("laudos/<int:ltcat_pk>/anexos/<int:pk>/excluir/", views.AnexoDeleteView.as_view(), name="anexo_delete"),

    # ═══ PROFISSIONAIS RESPONSÁVEIS ═══
    path('<int:ltcat_pk>/responsaveis/vincular/', views.ajax_vincular_responsavel, name='ajax_vincular_responsavel'),
    path('<int:ltcat_pk>/responsaveis/<int:pk>/desvincular/', views.ajax_desvincular_responsavel, name='ajax_desvincular_responsavel'),
    path('profissional/<int:pk>/salvar-assinatura/', views.ajax_salvar_assinatura, name='ajax_salvar_assinatura'),
    path('profissional/<int:pk>/limpar-assinatura/', views.ajax_limpar_assinatura, name='ajax_limpar_assinatura'),
    path('api/profissional-por-funcionario/', views.ajax_buscar_profissional_por_funcionario, name='ajax_profissional_por_funcionario'),

    # API AJAX
    path("api/locais-por-empresa/", views.ajax_locais_por_empresa, name="ajax_locais_por_empresa"),
    path("api/buscar-logradouros/", views.ajax_buscar_logradouros, name="ajax_buscar_logradouros"),
    path("locais/novo/bulk/", views.ajax_local_create_bulk, name="local_create_bulk"),
    path("api/dados-cliente/", views.ajax_dados_cliente, name="ajax_dados_cliente"),
    path('<int:ltcat_pk>/locais/vincular/', views.ajax_vincular_locais_documento, name='ajax_vincular_locais_documento'),
    path('<int:ltcat_pk>/locais/<int:pk>/desvincular/', views.ajax_desvincular_local_documento, name='ajax_desvincular_local_documento'),
    path('<int:ltcat_pk>/locais/<int:pk>/toggle-principal/', views.ajax_toggle_principal_local, name='ajax_toggle_principal_local'),
    # AJAX - Info Cargo/Função
    path('ajax/cargo-info/', ajax_cargo_info, name='ajax_cargo_info'),
    path('ajax/funcao-st-info/', ajax_funcao_st_info, name='ajax_funcao_st_info'),

    # PDF
    path("laudos/<int:pk>/pdf/", views.gerar_pdf_ltcat, name="gerar_pdf"),
]
