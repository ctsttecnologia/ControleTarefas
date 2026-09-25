# core/urls.py

from django.urls import path

from core.views_monitoramento import monitoramento_api, monitoramento_view
from . import views
from core.views import AssinaturaRemotaView, GerarLinkAssinaturaView, sem_funcionario_view

app_name = 'core'

urlpatterns = [
    path('selecionar-filial/', views.SelecionarFilialView.as_view(), name='selecionar_filial'),
    path('set/', views.SetFilialView.as_view(), name='set_filial'),

    # Download seguro genérico para TODOS os apps
    path('download/<str:app>/<str:model>/<int:pk>/<str:field>/',
         views.SecureFileDownloadView.as_view(), name='secure_download'),
    
    path('sem-funcionario/', sem_funcionario_view, name='sem_funcionario'),

    # Erros personalizados
    path('400/', views.error_400_view, name='error_400'),

    # Monitoramento
    path('monitoramento/', monitoramento_view, name='monitoramento'),
    path('monitoramento/api/', monitoramento_api, name='monitoramento_api'),
    path('monitoramento/dashboard/', monitoramento_view, name='dashboard'),

    path('politica-privacidade/', views.PoliticaPrivacidadeView.as_view(), name='politica_privacidade',),

    path('core/assinatura-remota/gerar/<str:app_label>/<str:model_name>/<int:object_id>/', GerarLinkAssinaturaView.as_view(), name='gerar_link_assinatura',),
    path('core/assinatura-remota/<uuid:token>/', AssinaturaRemotaView.as_view(), name='assinatura_remota',),
]
