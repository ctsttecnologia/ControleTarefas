from django.urls import path
from . import views

app_name = 'cadastro'

urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path('logradouro/', views.logradouro, name='logradouro'),
    path('cadastro/editar/<int:pk>/', views.editar_logradouro, name='editar_logradouro'),
    path('cadastro/excluir/<int:pk>/', views.excluir_logradouro, name='excluir_logradouro'),
]
