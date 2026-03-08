from django.urls import path
from . import views  # <-- A importação correta está aqui

app_name = 'treinamentos'

urlpatterns = [
    # --- Suas URLs de CRUD existentes ---
    path('', views.TreinamentoListView.as_view(), name='treinamento_list'),
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
    path('verificar/<uuid:protocolo>/', views.VerificarCertificadoView.as_view(), name='verificar_certificado'),
    # 2. URL privada para a página de coleta de assinatura
    path('assinatura/<str:token>/', views.PaginaAssinaturaView.as_view(), name='pagina_assinatura'),
    # 3. URL para o admin/gestor gerar o PDF de um participante
    path('participante/<int:pk>/gerar-certificado/', views.GerarCertificadoPDFView.as_view(), name='gerar_certificado_participante' ),
    # =================================================================
    # EAD — Catálogo e Área do Aluno
    # =================================================================
    # Catálogo público de cursos
    path('ead/', views.EADCatalogoView.as_view(), name='ead_catalogo'),
    path('ead/curso/<slug:slug>/', views.EADCursoDetailView.as_view(), name='ead_curso_detail'),
    # Área do aluno (logado)
    path('ead/meus-cursos/', views.EADMeusCursosView.as_view(), name='ead_meus_cursos'),
    path('ead/matricular/<slug:slug>/', views.EADMatricularView.as_view(), name='ead_matricular'),
    # Assistir aula (player)
    path('ead/aula/<int:pk>/', views.EADAulaPlayerView.as_view(), name='ead_aula_player'),
    # API de progresso (HTMX/AJAX)
    path('ead/aula/<int:pk>/progresso/', views.EADSalvarProgressoView.as_view(), name='ead_salvar_progresso'),
    path('ead/aula/<int:pk>/concluir/', views.EADConcluirAulaView.as_view(), name='ead_concluir_aula'),
    # Avaliação
    path('ead/avaliacao/<int:matricula_id>/', views.EADAvaliacaoView.as_view(), name='ead_avaliacao'),
    path('ead/avaliacao/<int:tentativa_id>/resultado/', views.EADResultadoView.as_view(), name='ead_resultado'),
    # Certificado EAD
    path('ead/certificado/<uuid:uuid>/', views.EADCertificadoView.as_view(), name='certificado_ead_detail'),
        # =================================================================
    # GESTÃO DE AVALIAÇÕES (Gestor)
    # =================================================================
    path( 'ead/gestao/curso/<slug:slug>/avaliacoes/', views.GestaoAvaliacoesCursoView.as_view(), name='gestao_avaliacoes_curso',),
    path('ead/gestao/tentativa/<int:tentativa_id>/', views.GestaoTentativaDetailView.as_view(), name='gestao_tentativa_detail',),
    path('ead/gestao/tentativa/<int:tentativa_id>/imprimir/', views.GestaoImprimirProvaView.as_view(), name='gestao_imprimir_prova', ),
    path('ead/gestao/matricula/<int:matricula_id>/liberar-tentativa/', views.GestaoLiberarTentativaView.as_view(), name='gestao_liberar_tentativa',),
    path('ead/gestao/matricula/<int:matricula_id>/gerar-certificado/', views.GestaoGerarCertificadoEADView.as_view(), name='gestao_gerar_certificado_ead', ),

]
