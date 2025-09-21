
# ferramentas/urls.py
from django.urls import path
from . import views

app_name = 'ferramentas'

urlpatterns = [
    path('', views.FerramentaListView.as_view(), name='ferramenta_list'),
    path('nova/', views.FerramentaCreateView.as_view(), name='ferramenta_create'),
    path('<int:pk>/', views.FerramentaDetailView.as_view(), name='ferramenta_detail'),
    path('<int:pk>/editar/', views.FerramentaUpdateView.as_view(), name='ferramenta_update'),
    path('<int:ferramenta_pk>/retirar/', views.RetiradaCreateView.as_view(), name='ferramenta_retirar'),
    path('movimentacao/<int:pk>/devolver/', views.DevolucaoUpdateView.as_view(), name='ferramenta_devolver'),
    path('<int:pk>/inativar/', views.InativarFerramentaView.as_view(), name='ferramenta_inativar'),
    
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    path('<int:pk>/iniciar-manutencao/', views.IniciarManutencaoView.as_view(), name='iniciar_manutencao'),
    path('<int:pk>/finalizar-manutencao/', views.FinalizarManutencaoView.as_view(), name='finalizar_manutencao'),

    # NOVAS ROTAS PARA IMPORTAÇÃO
    path('importar/', views.ImportarFerramentasView.as_view(), name='importar_ferramentas'),
    path('importar/template/', views.DownloadTemplateView.as_view(), name='download_template'),
]
    
