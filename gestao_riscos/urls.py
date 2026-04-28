# gestao_riscos/urls.py

from django.urls import path

from . import views


app_name = 'gestao_riscos'

urlpatterns = [
    # =========================================================================
    # DASHBOARD
    # =========================================================================
    path('', views.GestaoRiscosDashboardView.as_view(), name='lista_riscos',),

    # =========================================================================
    # INCIDENTES
    # =========================================================================
    path('incidentes/registrar/', views.RegistrarIncidenteView.as_view(),name='registrar_incidente',),

    # =========================================================================
    # INSPECOES
    # =========================================================================
    path('inspecoes/agendar/', views.AgendarInspecaoView.as_view(), name='agendar_inspecao',),
    path('inspecao/propostas/', views.ListaInspecoesPropostasView.as_view(), name='lista_inspecoes_propostas',),
    path('inspecao/<int:pk>/confirmar/', views.ConfirmarInspecaoView.as_view(), name='inspecao_confirmar',),
    path('inspecao/<int:pk>/detalhe/', views.InspecaoDetailView.as_view(), name='inspecao_detalhe',),
    path('inspecao/<int:pk>/completar/', views.CompletarInspecaoView.as_view(), name='inspecao_completar',),

    # =========================================================================
    # CALENDARIO E APIS
    # =========================================================================
    path('calendario/', views.CalendarioView.as_view(), name='calendario',),
    path('api/inspecao-events/', views.InspecaoEventsApiView.as_view(), name='inspecao_events_api',),
    path('api/entregas-por-equipamento/', views.EntregasPorEquipamentoView.as_view(), name='entregas_por_equipamento',),

    # =========================================================================
    # CARTAO DE BLOQUEIO (TAG) - CRUD
    # =========================================================================
    path('cartoes/',views.CartaoTagListView.as_view(), name='cartao_tag_list',),
    path('cartoes/novo/', views.CartaoTagCreateView.as_view(), name='cartao_tag_create',),
    path('cartoes/<int:pk>/', views.CartaoTagDetailView.as_view(),name='cartao_tag_detail',),
    path('cartoes/<int:pk>/editar/', views.CartaoTagUpdateView.as_view(), name='cartao_tag_update',),
    path('cartoes/<int:pk>/deletar/', views.CartaoTagDeleteView.as_view(), name='cartao_tag_delete',),

    # =========================================================================
    # TIPO DE RISCO - CRUD
    # =========================================================================
    path('tipos-risco/', views.TipoRiscoListView.as_view(), name='tipo_risco_list',),
    path('tipos-risco/novo/', views.TipoRiscoCreateView.as_view(), name='tipo_risco_create',),
    path('tipos-risco/<int:pk>/editar/', views.TipoRiscoUpdateView.as_view(), name='tipo_risco_update',),
    path('tipos-risco/<int:pk>/excluir/', views.TipoRiscoDeleteView.as_view(), name='tipo_risco_delete',),
    path('tipos-risco/<int:pk>/toggle-ativo/', views.TipoRiscoToggleAtivoView.as_view(), name='tipo_risco_toggle_ativo',),
    path('tipos-risco/popular-padrao/', views.TipoRiscoPopularView.as_view(), name='tipo_risco_popular',),
]
