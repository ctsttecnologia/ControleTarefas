# logradouro/urls.py

from django.urls import path

from logradouro.admin import consulta_cep
from .views import (
    DownloadErroRelatorioView,
    DownloadTemplateView,
    LogradouroListView, 
    LogradouroCreateView, 
    LogradouroUpdateView, 
    LogradouroDeleteView,
    LogradouroExportExcelView,
    UploadLogradourosView
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
    # busca de cep
    path('consulta-cep/', consulta_cep, name='consulta_cep'),
    # Caminho para upload e de planilha para inserção de dados em massa
    path('logradouros/upload/', UploadLogradourosView.as_view(), name='upload_logradouros'),
    path('logradouros/upload/template/', DownloadTemplateView.as_view(), name='download_logradouro_template'),
    path('logradouros/upload/download-erros/', DownloadErroRelatorioView.as_view(), name='download_erros_logradouro'),
]
