
# G:\Projetos\treinamentos\urls.py

from django.urls import path
from .views import (
    # Views de Treinamento
    TreinamentoListView,
    DetalheTreinamentoView,
    CriarTreinamentoView,
    EditarTreinamentoView,
    ExcluirTreinamentoView,

    # Views de Tipo de Curso
    TipoCursoListView,
    CriarTipoCursoView,
    EditarTipoCursoView,
    ExcluirTipoCursoView,

    # View de Relatório
    RelatorioTreinamentosView,
    DashboardView,
)

app_name = 'treinamentos'

urlpatterns = [
    # --- URLs para Treinamentos ---
    # Lista todos os treinamentos (Página principal)
    path('', TreinamentoListView.as_view(), name='lista_treinamentos'),
    # Cria um novo treinamento
    path('criar_treinamento/', CriarTreinamentoView.as_view(), name='criar_treinamento'),
    # Detalhes de um treinamento específico
    path('<int:pk>/', DetalheTreinamentoView.as_view(), name='detalhe_treinamento'),
    # Edita um treinamento existente
    path('<int:pk>/editar/', EditarTreinamentoView.as_view(), name='editar_treinamento'),
    # Exclui um treinamento
    path('<int:pk>/excluir/', ExcluirTreinamentoView.as_view(), name='excluir_treinamento'),
    # --- URLs para Tipos de Curso ---
    # Lista todos os tipos de curso
    path('tipos-de-curso/', TipoCursoListView.as_view(), name='lista_tipo_curso'),
    # Cria um novo tipo de curso
    path('criar_tipo_curso/', CriarTipoCursoView.as_view(), name='criar_tipo_curso'),
    # Edita um tipo de curso existente
    path('tipos-de-curso/<int:pk>/editar/', EditarTipoCursoView.as_view(), name='editar_tipo_curso'),
    # Exclui um tipo de curso
    path('tipos-de-curso/<int:pk>/excluir/', ExcluirTipoCursoView.as_view(), name='excluir_tipo_curso'),
    # --- URLs para Relatórios ---
    path('relatorios/treinamentos/', RelatorioTreinamentosView.as_view(), name='relatorio_treinamentos'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]

