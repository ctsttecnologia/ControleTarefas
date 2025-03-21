from django.urls import path
from . import views


urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path('cadastro/editar/<int:pk>/', views.editar_logradouro, name='editar_logradouro'),
    path('cadastro/excluir/<int:pk>/', views.excluir_logradouro, name='excluir_logradouro'),
]
