from django.urls import path
from . import views

app_name = 'logradouro'

urlpatterns = [
    path('logradouro/', views.listar_logradouros, name='listar'),
    path('cadastrar/', views.cadastrar_logradouro, name='cadastrar'),
    path('editar/<int:pk>/', views.editar_logradouro, name='editar'),
    path('excluir/<int:pk>/', views.excluir_logradouro, name='excluir'),
    path('exportar-excel/', views.exportar_excel, name='exportar_excel'),
]