# epi/urls.py

from django.urls import path
from . import views
from .views import (
    CartaoTagListView,
    CartaoTagCreateView,
    CartaoTagDetailView,
    CartaoTagUpdateView,
    CartaoTagDeleteView,
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

    # --- ROTAS DO CALENDÁRIO (ESTAVAM FALTANDO) ---
    path('calendario/', views.CalendarioView.as_view(), name='calendario'),
    path('api/eventos-inspecao/', views.inspecao_events_api, name='api_inspecao_events'),

    # --- URLs para o CRUD de Cartão TAG ---
    path('cartoes/', CartaoTagListView.as_view(), name='cartao_tag_list'),
    path('cartoes/novo/', CartaoTagCreateView.as_view(), name='cartao_tag_create'),
    path('cartoes/<int:pk>/', CartaoTagDetailView.as_view(), name='cartao_tag_detail'),
    path('cartoes/<int:pk>/editar/', CartaoTagUpdateView.as_view(), name='cartao_tag_update'),
    path('cartoes/<int:pk>/deletar/', CartaoTagDeleteView.as_view(), name='cartao_tag_delete'),
]
