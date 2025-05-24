from django.urls import path
from . import views
from .views import relatorio_tarefas

app_name = 'tarefas'

urlpatterns = [
    
    path('tarefas/', views.tarefas, name='tarefas'),
    path('tarefas/', views.listar_tarefas, name='listar_tarefas'),
    path('criar_tarefa/', views.criar_tarefa, name='criar_tarefa'),
    path('editar/<int:pk>/', views.editar_tarefa, name='editar_tarefa'),
    path('excluir/<int:pk>/', views.excluir_tarefa, name='excluir_tarefa'),
    path('relatorio/', relatorio_tarefas, name='relatorio_tarefas'),
    path('', views.dashboard, name='dashboard'),
    path('tarefa/<int:pk>/', views.tarefa_detail, name='tarefa_detail'),
    path('tarefa/<int:pk>/atualizar_status/', views.atualizar_status, name='atualizar_status'),
    path('calendario/', views.calendario_tarefas, name='calendario_tarefas'),
]