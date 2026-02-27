# tarefas/urls.py

# tarefas/urls.py

from django.urls import path, include
from rest_framework import routers

from .api import TarefaViewSet
from . import views

router = routers.DefaultRouter()
router.register(r'tarefas', TarefaViewSet)

app_name = 'tarefas'

urlpatterns = [
    # --- CRUD ---
    path('', views.TarefaListView.as_view(), name='listar_tarefas'),
    path('criar/', views.TarefaCreateView.as_view(), name='criar_tarefa'),
    path('<int:pk>/detalhe/', views.TarefaDetailView.as_view(), name='tarefa_detail'),
    path('<int:pk>/editar/', views.TarefaUpdateView.as_view(), name='editar_tarefa'),
    path('<int:pk>/excluir/', views.TarefaDeleteView.as_view(), name='excluir_tarefa'),
    path('<int:pk>/concluir/', views.ConcluirTarefaView.as_view(), name='concluir_tarefa'),

    # --- Visualizações ---
    path('kanban/', views.KanbanView.as_view(), name='kanban_board'),
    path('calendario/', views.CalendarioTarefasView.as_view(), name='calendario_tarefas'),
    path('dashboard/', views.DashboardAnaliticoView.as_view(), name='dashboard'),
    path('relatorio/', views.RelatorioTarefasView.as_view(), name='relatorio_tarefas'),

    # --- Admin ---
    path('admin/todas/', views.TarefaAdminListView.as_view(), name='tarefas_admin'),

    # --- API ---
    path('api/', include(router.urls)),
    path('api/update-status/', views.UpdateTaskStatusView.as_view(), name='update_task_status'),
]

