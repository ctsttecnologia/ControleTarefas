
from . import views
from django.urls import path, include
from rest_framework import routers
from .api import TarefaViewSet
from .views import (KanbanView, 
                    DashboardAnaliticoView, 
                    RelatorioTarefasView, 
                    TarefaCreateView,
                    TarefaDeleteView, 
                    TarefaDetailView,
                    TarefaUpdateView, 
                    UpdateTaskStatusView,
                )
router = routers.DefaultRouter()
router.register(r'tarefas', TarefaViewSet)

app_name = 'tarefas'

urlpatterns = [
   
    path('', views.TarefaListView.as_view(), name='listar_tarefas'),
    path('admin/todas/', views.TarefaAdminListView.as_view(), name='tarefas_admin'),
    path('criar/', TarefaCreateView.as_view(), name='criar_tarefa'),
    path('<int:pk>/editar/', views.TarefaUpdateView.as_view(), name='editar_tarefa'), 
    path('<int:pk>/excluir/', TarefaDeleteView.as_view(), name='excluir_tarefa'),
    path('dashboard/analitico/', DashboardAnaliticoView.as_view(), name='dashboard_analitico'),
    path('<int:pk>/', views.TarefaDetailView.as_view(), name='tarefa_detail'),
 
    path('calendario/', views.CalendarioTarefasView.as_view(), name='calendario_tarefas'),

    path('api/', include(router.urls)),
    path('relatorio/', RelatorioTarefasView.as_view(), name='relatorio_tarefas'),
    path('kanban/', KanbanView.as_view(), name='kanban_board'),
    path('kanban/', KanbanView.as_view(), name='kanban'),
    path('<int:pk>/editar/', TarefaUpdateView.as_view(), name='tarefa_update'),
    path('api/update-status/', views.UpdateTaskStatusView.as_view(), name='update_task_status'),



    



]

