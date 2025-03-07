from django.urls import path
from . import views

urlpatterns = [
    path('cliente/', views.cliente, name='cliente'),
    path('lista_clientes/', views.lista_clientes, name='lista_clientes'),
    path('cadastro_cliente/', views.cadastro_cliente, name='cadastro_cliente'),
    path('salvar_cliente/', views.salvar_cliente, name='salvar_cliente'),
]