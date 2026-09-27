# ferramentas/urls.py
from django.urls import path
from . import views

app_name = 'ferramentas'

urlpatterns = [
    # -- URLs Gerais e Dashboard --
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # -- URLs de Ferramentas Individuais --
    path('', views.FerramentaListView.as_view(), name='ferramenta_list'),
    path('nova/', views.FerramentaCreateView.as_view(), name='ferramenta_create'),
    path('<int:pk>/', views.FerramentaDetailView.as_view(), name='ferramenta_detail'),
    path('<int:pk>/editar/', views.FerramentaUpdateView.as_view(), name='ferramenta_update'),
    path('<int:pk>/inativar/', views.InativarFerramentaView.as_view(), name='ferramenta_inativar'),
    path('<int:pk>/iniciar-manutencao/', views.IniciarManutencaoView.as_view(), name='iniciar_manutencao'),
    path('<int:pk>/finalizar-manutencao/', views.FinalizarManutencaoView.as_view(), name='finalizar_manutencao'),

    # -- URLs de Malas de Ferramentas --
    path('malas/', views.MalaListView.as_view(), name='mala_list'),
    path('malas/nova/', views.MalaCreateView.as_view(), name='mala_create'),
    path('malas/<int:pk>/', views.MalaDetailView.as_view(), name='mala_detail'),
    path('malas/<int:pk>/editar/', views.MalaUpdateView.as_view(), name='mala_update'),

    # -- URLs de Movimentação (Retirada e Devolução) --   
    path('ferramentas/<int:ferramenta_pk>/retirar/', views.MovimentacaoCreateView.as_view(), name='retirar_ferramenta'),
    path('malas/<int:mala_pk>/retirar/', views.MovimentacaoCreateView.as_view(), name='retirar_mala'),
    path('movimentacoes/<int:pk>/devolver/', views.DevolucaoUpdateView.as_view(), name='devolver_movimentacao'),


    # -- URLs Utilitárias (QR Code, Importação, etc.) --
    path('qrcodes/gerar/', views.GerarQRCodesView.as_view(), name='gerar_qrcodes_view'),
    path('qrcodes/imprimir/', views.ImprimirQRCodesView.as_view(), name='imprimir_qrcodes'),
    path('scan/<str:codigo_identificacao>/', views.ResultadoScanView.as_view(), name='resultado_scan'),
    path('importar/', views.ImportarFerramentasView.as_view(), name='importar_ferramentas'),
    path('importar/template/', views.DownloadTemplateView.as_view(), name='download_template'),

    # -- URLs de Termos de Responsabilidade --
    path('termos/', views.TermoListView.as_view(), name='termoderesponsabilidade_list'),
    path('termos/criar/', views.CriarTermoResponsabilidadeView.as_view(), name='criar_termo_responsabilidade'),
    path('termos/<int:pk>/', views.TermoDetailView.as_view(), name='termo_detail'),
    path('termos/<int:pk>/pdf/', views.DownloadTermoPDFView.as_view(), name='termo_pdf_download'),
    path('termos/download-lote/', views.DownloadTermosLoteView.as_view(), name='termo_download_lote'),
    path('termos/<int:pk>/reverter/', views.ReverterTermoView.as_view(), name='termo_reverter'),
    path('termos/<int:pk>/enviar-link/', views.EnviarLinkAssinaturaView.as_view(), name='enviar_link_assinatura'),
    
]

