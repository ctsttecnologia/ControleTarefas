
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
    RelatorioTreinamentoWordView,
    RelatorioGeralExcelView, 

)

app_name = 'treinamentos'

urlpatterns = [

    # Lista todos os treinamentos (Página principal)
    path('', TreinamentoListView.as_view(), name='lista_treinamentos'),
    path('criar_treinamento/', CriarTreinamentoView.as_view(), name='criar_treinamento'),
    path('<int:pk>/', DetalheTreinamentoView.as_view(), name='detalhe_treinamento'),
    path('<int:pk>/editar/', EditarTreinamentoView.as_view(), name='editar_treinamento'),
    path('<int:pk>/excluir/', ExcluirTreinamentoView.as_view(), name='excluir_treinamento'),

    # Lista todos os tipos de curso
    path('tipos-de-curso/', TipoCursoListView.as_view(), name='lista_tipos_curso'),
    path('criar_tipo_curso/', CriarTipoCursoView.as_view(), name='criar_tipo_curso'),
    path('tipos-de-curso/<int:pk>/editar/', EditarTipoCursoView.as_view(), name='editar_tipo_curso'),
    path('tipos-de-curso/<int:pk>/excluir/', ExcluirTipoCursoView.as_view(), name='excluir_tipo_curso'),

    path('relatorio/', RelatorioTreinamentosView.as_view(), name='relatorio_treinamentos'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('treinamento/<int:pk>/relatorio/word/', RelatorioTreinamentoWordView.as_view(), name='relatorio_treinamento_word'),
    path('relatorio/geral/excel/', RelatorioGeralExcelView.as_view(), name='relatorio_geral_excel'),
 

]

