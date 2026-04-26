# core/urls.py

from django.urls import path
from . import views
from core.views import sem_funcionario_view

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

]
