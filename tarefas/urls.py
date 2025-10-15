# tarefas/urls.py

from django.urls import path, include
from rest_framework import routers
from . import views
from .api import TarefaViewSet
from .views import (
    KanbanView, 
    DashboardAnaliticoView, 
    RelatorioTarefasView, 
    TarefaCreateView,
    TarefaDeleteView, 
    TarefaDetailView,
    TarefaUpdateView, 
    UpdateTaskStatusView,
    TarefaListView, # Adicionado para clareza
    TarefaAdminListView, # Adicionado para clareza
    CalendarioTarefasView, # Adicionado para clareza
    ConcluirTarefaView,
 
)

router = routers.DefaultRouter()
router.register(r'tarefas', TarefaViewSet)

app_name = 'tarefas'

urlpatterns = [
    path('', TarefaListView.as_view(), name='listar_tarefas'),
    path('admin/todas/', TarefaAdminListView.as_view(), name='tarefas_admin'),
    path('criar/', TarefaCreateView.as_view(), name='criar_tarefa'),
    path('<int:pk>/detalhe/', TarefaDetailView.as_view(), name='tarefa_detail'),

    
    # Rota de edição (unificada)
    path('<int:pk>/editar/', TarefaUpdateView.as_view(), name='editar_tarefa'), 
    
    path('<int:pk>/excluir/', TarefaDeleteView.as_view(), name='excluir_tarefa'),
    
    # --- ROTA FALTANTE ADICIONADA AQUI ---
    # Esta é a linha que corrige o erro NoReverseMatch.
    # Certifique-se de que a view 'views.concluir_tarefa_view' existe no seu 'views.py'.
    path('concluir/<int:pk>/', views.ConcluirTarefaView.as_view, name='concluir_tarefa'),

    # Outras rotas do seu app
    path('dashboard/analitico/', DashboardAnaliticoView.as_view(), name='dashboard'),
    path('calendario/', CalendarioTarefasView.as_view(), name='calendario_tarefas'),
    path('relatorio/', RelatorioTarefasView.as_view(), name='relatorio_tarefas'),
    path('kanban/', KanbanView.as_view(), name='kanban_board'),
    
    # Rotas da API
    path('api/', include(router.urls)),
    path('api/update-status/', UpdateTaskStatusView.as_view(), name='update_task_status'),
]

