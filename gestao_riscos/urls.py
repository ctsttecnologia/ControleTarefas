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
    # Rota para agendar inspeção aponta para a CreateView de Inspeção
    path('inspecoes/agendar/', views.AgendarInspecaoView.as_view(), name='agendar_inspecao'),

     # --- URLs para o CRUD de Cartão TAG ---
    path('cartoes/', CartaoTagListView.as_view(), name='cartao_tag_list'),
    path('cartoes/novo/', CartaoTagCreateView.as_view(), name='cartao_tag_create'),
    path('cartoes/<int:pk>/', CartaoTagDetailView.as_view(), name='cartao_tag_detail'),
    path('cartoes/<int:pk>/editar/', CartaoTagUpdateView.as_view(), name='cartao_tag_update'),
    path('cartoes/<int:pk>/deletar/', CartaoTagDeleteView.as_view(), name='cartao_tag_delete'),
]


