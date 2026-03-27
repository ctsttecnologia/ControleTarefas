
from django.urls import path
from .views import (
    ClienteDetailView,
    ClienteListView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDeleteView,
    ExportarClientesExcelView,
    cliente_autocomplete_view, download_modelo_view, importacao_massa_view, ajax_buscar_logradouros
)


app_name = 'cliente'

urlpatterns = [
    path('', ClienteListView.as_view(), name='lista_clientes'),
    path('cadastrar/', ClienteCreateView.as_view(), name='cliente_create'),
    path('editar/<int:pk>/', ClienteUpdateView.as_view(), name='editar_cliente'),
    path('excluir/<int:pk>/', ClienteDeleteView.as_view(), name='excluir_cliente'),
    path('exportar/', ExportarClientesExcelView.as_view(), name='exportar_excel'),
    path('detalhe/<int:pk>/', ClienteDetailView.as_view(), name='cliente_detail'),

    # --- NOVA URL PARA O AUTOCOMPLETAR ---
    path('api/autocomplete/', cliente_autocomplete_view, name='cliente-autocomplete'),

    path('ajax/logradouros/', ajax_buscar_logradouros, name='ajax_buscar_logradouros'),
    path("importacao/modelo/", download_modelo_view, name='download_modelo_importacao'),
    path("importacao/", importacao_massa_view, name='importacao_massa'),
]

