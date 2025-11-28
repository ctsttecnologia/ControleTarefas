
from django.urls import path
from . import views

# OBRIGATÓRIO: Define o namespace 'dashboard'
app_name = 'dashboard' 

urlpatterns = [
    # Exemplo de como devem estar suas URLs para bater com o seu dicionário:
    path('geral/', views.dashboard_geral_view, name='dashboard_geral'),
    path('treinamentos/', views.dashboard_treinamentos_view, name='dashboard_treinamentos'),
    path('tarefas/', views.dashboard_tarefas_view, name='dashboard_tarefas'),
    path('epi/', views.dashboard_epi_view, name='dashboard_epi'),
    path('documentos/', views.dashboard_documentos_view, name='dashboard_documentos'),
]

