from django.urls import path
from . import views



urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
   
    path('estados/', views.lista_estados, name='lista_estados'),
    path('estados/novo/', views.novo_estado, name='novo_estado'),
    path('estados/editar/<int:pk>/', views.editar_estado, name='editar_estado'),
    path('estados/deletar/<int:pk>/', views.deletar_estado, name='deletar_estado'),
    

    path('logradouros/', views.lista_logradouros, name='lista_logradouros'),
    path('logradouros/novo/', views.novo_logradouro, name='novo_logradouro'),
    path('logradouros/editar/<int:pk>/', views.editar_logradouro, name='editar_logradouro'),
    path('logradouros/deletar/<int:pk>/', views.deletar_logradouro, name='deletar_logradouro'),
]