from django.urls import path
from . import views

app_name = 'tarefas'

urlpatterns = [
    
    path('tarefas/', views.tarefas, name='tarefas'),
    path('criar_tarefa/', views.criar_tarefa, name='criar_tarefa'),
    
    path('editar/<int:id>/', views.editar_tarefa, name='editar_tarefa'),
    path('excluir/<int:id>/', views.excluir_tarefa, name='excluir_tarefa'),
    
]