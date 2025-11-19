
from django.urls import path
from .views import (
    ClienteDetailView,
    ClienteListView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDeleteView,
    ExportarClientesExcelView,
)

app_name = 'cliente'

urlpatterns = [
    path('', ClienteListView.as_view(), name='lista_clientes'),
    path('cadastrar/', ClienteCreateView.as_view(), name='cadastro_cliente'),
    path('editar/<int:pk>/', ClienteUpdateView.as_view(), name='editar_cliente'),
    path('excluir/<int:pk>/', ClienteDeleteView.as_view(), name='excluir_cliente'),
    path('exportar/', ExportarClientesExcelView.as_view(), name='exportar_excel'),
    path('detalhe/<int:pk>/', ClienteDetailView.as_view(), name='cliente_detail'),
]
