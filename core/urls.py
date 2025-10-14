
# core/urls.py

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('selecionar-filial/', views.SelecionarFilialView.as_view(), name='selecionar_filial'),
    path('set/', views.SetFilialView.as_view(), name='set_filial'),
]
