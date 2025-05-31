from django.urls import path
from . import views

app_name = 'treinamentos'

urlpatterns = [
    # Treinamento URLs
    path('', views.listar_treinamentos, name='listar_treinamentos'),
    path('cadastrar/', views.cadastrar_treinamento, name='cadastrar_treinamento'),
    path('<int:pk>/', views.detalhes_treinamento, name='detalhes_treinamento'),
    path('<int:pk>/editar/', views.editar_treinamento, name='editar_treinamento'),
    path('<int:pk>/excluir/', views.excluir_treinamento, name='excluir_treinamento'),
    path('tipos/', views.listar_tipos_treinamento, name='listar_tipos_treinamento'),
    path('treinamentos_disponiveis/', views.treinamentos_disponiveis, name='treinamentos_disponiveis'),
    path('colaborador/<int:colaborador_id>/treinamentos/', views.treinamentos_colaborador, name='treinamentos_colaborador'),
    
    # Busca
    path('buscar/', views.buscar_treinamentos, name='buscar_treinamentos'),
]