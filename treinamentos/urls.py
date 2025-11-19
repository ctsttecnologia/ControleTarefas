from django.urls import path
from . import views  # <-- A importação correta está aqui

app_name = 'treinamentos'

urlpatterns = [
    # --- Suas URLs de CRUD existentes ---
    path('', views.TreinamentoListView.as_view(), name='lista_treinamentos'),
    path('criar/', views.CriarTreinamentoView.as_view(), name='criar_treinamento'),
    path('<int:pk>/', views.DetalheTreinamentoView.as_view(), name='detalhe_treinamento'),
    path('<int:pk>/editar/', views.EditarTreinamentoView.as_view(), name='editar_treinamento'),
    path('<int:pk>/excluir/', views.ExcluirTreinamentoView.as_view(), name='excluir_treinamento'),

    # Tipos de Curso
    path('tipos/', views.TipoCursoListView.as_view(), name='lista_tipos_curso'),
    path('tipos/criar/', views.CriarTipoCursoView.as_view(), name='criar_tipo_curso'),
    path('tipos/<int:pk>/editar/', views.EditarTipoCursoView.as_view(), name='editar_tipo_curso'),
    path('tipos/<int:pk>/excluir/', views.ExcluirTipoCursoView.as_view(), name='excluir_tipo_curso'),
    
    # Relatórios
    path('relatorios/', views.RelatorioTreinamentosView.as_view(), name='relatorio_treinamentos'),
    path('<int:pk>/relatorio-word/', views.RelatorioTreinamentoWordView.as_view(), name='relatorio_treinamento_word'),
    path('relatorios/excel/', views.RelatorioGeralExcelView.as_view(), name='relatorio_geral_excel'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    
    # 1. URL pública para verificação do QR Code
    path(
        'verificar/<uuid:protocolo>/', 
        views.VerificarCertificadoView.as_view(), 
        name='verificar_certificado'
    ),
    
    # 2. URL privada para a página de coleta de assinatura
    path(
        'assinatura/<str:token>/', 
        views.PaginaAssinaturaView.as_view(), 
        name='pagina_assinatura'
    ),
    
    # 3. URL para o admin/gestor gerar o PDF de um participante
    path(
        'participante/<int:pk>/gerar-certificado/', 
        views.GerarCertificadoPDFView.as_view(), 
        name='gerar_certificado_participante'
    ),
]
