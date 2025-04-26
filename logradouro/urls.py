from django.urls import path
from . import views

app_name = 'logradouro'

urlpatterns = [
    path('logradouro/', views.listar_logradouros, name='listar_logradouros'),
    path('cadastrar/', views.cadastrar_logradouro, name='cadastrar_logradouro'),
    path('editar/<int:pk>/', views.editar_logradouro, name='editar_logradouro'),
    path('excluir/<int:pk>/', views.excluir_logradouro, name='excluir_logradouro'),
    path('exportar-excel/', views.exportar_excel, name='exportar_excel'),
]


