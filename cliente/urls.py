
from django.urls import path
from . import views

app_name = 'cliente'  # Adicionando namespace

urlpatterns = [
    path('', views.lista_clientes, name='lista_clientes'),  # Página principal
    path('cadastrar/', views.cadastro_cliente, name='cadastro_cliente'),
    path('editar/<int:pk>/', views.editar_cliente, name='editar_cliente'),
    path('excluir/<int:pk>/', views.excluir_cliente, name='excluir_cliente'),
    path('pesquisar/', views.pesquisar_clientes, name='pesquisar_clientes'),
    path('exportar-excel/', views.exportar_clientes_excel, name='exportar_excel'),
]