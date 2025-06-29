
from . import views
from django.urls import path, include
from rest_framework import routers
from .api import TarefaViewSet
from .views import (KanbanView, 
                    DashboardAnaliticoView, 
                    RelatorioTarefasView, 
                    TarefaCreateView, 
                    update_task_status)


router = routers.DefaultRouter()
router.register(r'tarefas', TarefaViewSet)


app_name = 'tarefas'

urlpatterns = [
   
    path('', views.listar_tarefas, name='listar_tarefas'),
    path('criar/', TarefaCreateView.as_view(), name='criar_tarefa'),
    path('editar/<int:pk>/', views.editar_tarefa, name='editar_tarefa'),
    path('excluir/<int:pk>/', views.excluir_tarefa, name='excluir_tarefa'),
    path('dashboard/analitico/', DashboardAnaliticoView.as_view(), name='dashboard_analitico'),
    path('tarefa/<int:pk>/', views.tarefa_detail, name='tarefa_detail'),
    path('tarefa/<int:pk>/atualizar_status/', views.atualizar_status, name='atualizar_status'),
    path('calendario/', views.calendario_tarefas, name='calendario_tarefas'),

    path('api/', include(router.urls)),
    path('relatorio/', RelatorioTarefasView.as_view(), name='relatorio_tarefas'),
    path('kanban/', KanbanView.as_view(), name='kanban_board'),
    path('api/update_task_status/', update_task_status, name='update_task_status'),
]

