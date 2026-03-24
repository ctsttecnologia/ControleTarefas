# epi/urls.py

from django.urls import path
from . import views
from .views import (
    CartaoTagListView,
    CartaoTagCreateView,
    CartaoTagDetailView,
    CartaoTagUpdateView,
    CartaoTagDeleteView,
    EntregasPorEquipamentoView,
)

app_name = 'gestao_riscos'

urlpatterns = [
    # Rota principal aponta para a view de Dashboard
    path('', views.GestaoRiscosDashboardView.as_view(), name='lista_riscos'),
    
    # Rota para registrar incidente aponta para a CreateView de Incidente
    path('incidentes/registrar/', views.RegistrarIncidenteView.as_view(), name='registrar_incidente'),
    
    # --- Rotas de Inspeção ---
    path('inspecoes/agendar/', views.AgendarInspecaoView.as_view(), name='agendar_inspecao'),
    path('inspecao/propostas/', views.ListaInspecoesPropostasView.as_view(), name='lista_inspecoes_propostas'),
    path('inspecao/<int:pk>/confirmar/', views.ConfirmarInspecaoView.as_view(), name='inspecao_confirmar'),
    path('inspecao/<int:pk>/detalhe/', views.InspecaoDetailView.as_view(), name='inspecao_detalhe'),
    path('inspecao/<int:pk>/completar/', views.CompletarInspecaoView.as_view(), name='inspecao_completar'),

    path('api/entregas-por-equipamento/', EntregasPorEquipamentoView.as_view(), name='entregas_por_equipamento'),

    # --- ROTAS DO CALENDÁRIO (ESTAVAM FALTANDO) ---
    path('calendario/', views.CalendarioView.as_view(), name='calendario'),
    path('api/inspecao-events/', views.InspecaoEventsApiView.as_view(), name='inspecao_events_api'),

    # --- URLs para o CRUD de Cartão TAG ---
    path('cartoes/', CartaoTagListView.as_view(), name='cartao_tag_list'),
    path('cartoes/novo/', CartaoTagCreateView.as_view(), name='cartao_tag_create'),
    path('cartoes/<int:pk>/', CartaoTagDetailView.as_view(), name='cartao_tag_detail'),
    path('cartoes/<int:pk>/editar/', CartaoTagUpdateView.as_view(), name='cartao_tag_update'),
    path('cartoes/<int:pk>/deletar/', CartaoTagDeleteView.as_view(), name='cartao_tag_delete'),

    # ========== TIPO DE RISCO ==========
    path('tipos-risco/', views.TipoRiscoListView.as_view(), name='tipo_risco_list'),
    path('tipos-risco/novo/', views.TipoRiscoCreateView.as_view(), name='tipo_risco_create'),
    path('tipos-risco/<int:pk>/editar/', views.TipoRiscoUpdateView.as_view(), name='tipo_risco_update'),
    path('tipos-risco/<int:pk>/excluir/', views.TipoRiscoDeleteView.as_view(), name='tipo_risco_delete'),
    path('tipos-risco/<int:pk>/toggle-ativo/', views.TipoRiscoToggleAtivoView.as_view(), name='tipo_risco_toggle_ativo'),
    path('tipos-risco/popular-padrao/', views.TipoRiscoPopularView.as_view(), name='tipo_risco_popular'),
]
