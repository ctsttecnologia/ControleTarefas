# ferramentas/urls.py
from django.urls import path
from . import views

app_name = 'ferramentas'

urlpatterns = [
    # -- URLs Gerais e Dashboard --
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # -- URLs de Ferramentas Individuais --
    # A lista agora é a raiz do app (ex: /ferramentas/)
    path('', views.FerramentaListView.as_view(), name='ferramenta_list'), 
    path('nova/', views.FerramentaCreateView.as_view(), name='ferramenta_create'),
    # O detalhe agora é /ferramentas/<pk>/
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
    path('retirar/ferramenta/<int:ferramenta_pk>/', views.MovimentacaoCreateView.as_view(), name='retirar_ferramenta'),
    path('retirar/mala/<int:mala_pk>/', views.MovimentacaoCreateView.as_view(), name='retirar_mala'),
    path('devolver/ferramenta/<int:pk>/', views.DevolucaoUpdateView.as_view(), name='devolver_ferramenta'),
    path('devolver/mala/<int:pk>/', views.MalaDevolucaoUpdateView.as_view(), name='mala_devolver'),

    # -- URLs Utilitárias (QR Code, Importação, etc.) --
    path('qrcodes/gerar/', views.GerarQRCodesView.as_view(), name='gerar_qrcodes_view'),
    path('qrcodes/imprimir/', views.ImprimirQRCodesView.as_view(), name='imprimir_qrcodes'),
    path('scan/<str:codigo_identificacao>/', views.ResultadoScanView.as_view(), name='resultado_scan'),
    path('importar/', views.ImportarFerramentasView.as_view(), name='importar_ferramentas'),
    path('importar/template/', views.DownloadTemplateView.as_view(), name='download_template'),
]