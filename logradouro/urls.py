# logradouro/urls.py

from django.urls import path
from .views import (
    LogradouroListView, 
    LogradouroCreateView, 
    LogradouroUpdateView, 
    LogradouroDeleteView,
    LogradouroExportExcelView
)

app_name = 'logradouro'

urlpatterns = [
    # Caminho para a lista de logradouros (página principal)
    path('', LogradouroListView.as_view(), name='listar_logradouros'),
    
    # Caminho para o formulário de cadastro
    path('cadastrar/', LogradouroCreateView.as_view(), name='cadastrar_logradouro'),
    
    # Caminho para editar um logradouro específico
    path('editar/<int:pk>/', LogradouroUpdateView.as_view(), name='editar_logradouro'),
    
    # Caminho para a página de confirmação de exclusão
    path('excluir/<int:pk>/', LogradouroDeleteView.as_view(), name='confirmar_exclusao'),
    
    # Caminho para a funcionalidade de exportar para Excel
    path('exportar-excel/', LogradouroExportExcelView.as_view(), name='exportar_excel'),
]
