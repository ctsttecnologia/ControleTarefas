
from . import views
from django.urls import path, include
from rest_framework import routers
from .api import TarefaViewSet
from .views import RelatorioTarefasPDF


router = routers.DefaultRouter()
router.register(r'tarefas', TarefaViewSet)

app_name = 'tarefas'

urlpatterns = [
    path('tarefas/', views.listar_tarefas, name='listar_tarefas'),  # Removida a duplicata
    path('criar_tarefa/', views.criar_tarefa, name='criar_tarefa'),
    path('editar/<int:pk>/', views.editar_tarefa, name='editar_tarefa'),
    path('excluir/<int:pk>/', views.excluir_tarefa, name='excluir_tarefa'),
    path('relatorio/', views.relatorio_tarefas, name='relatorio_tarefas'),  # Usando views.
    path('', views.dashboard, name='dashboard'),
    path('tarefa/<int:pk>/', views.tarefa_detail, name='tarefa_detail'),
    path('tarefa/<int:pk>/atualizar_status/', views.atualizar_status, name='atualizar_status'),
    path('calendario/', views.calendario_tarefas, name='calendario_tarefas'),

    path('api/', include(router.urls)),
    path('relatorio/', RelatorioTarefasPDF.as_view(), name='relatorio_tarefas'),
]

