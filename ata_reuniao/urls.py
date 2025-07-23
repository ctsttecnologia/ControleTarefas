from django.urls import path
from .views import (
    AtaReuniaoListView, AtaReuniaoCreateView, 
    AtaReuniaoUpdateView, AtaReuniaoDeleteView,
    AtaReuniaoDashboardView, AtaReuniaoPDFExportView, AtaReuniaoExcelExportView 
)

urlpatterns = [
    path('', AtaReuniaoListView.as_view(), name='ata_reuniao_list'),
    path('novo/', AtaReuniaoCreateView.as_view(), name='ata_reuniao_create'),
    path('editar/<int:pk>/', AtaReuniaoUpdateView.as_view(), name='ata_reuniao_update'),
    path('excluir/<int:pk>/', AtaReuniaoDeleteView.as_view(), name='ata_reuniao_delete'),
    
    # --- ROTAS ATUALIZADAS ---
    path('dashboard/', AtaReuniaoDashboardView.as_view(), name='ata_reuniao_dashboard'),
    path('exportar-pdf/', AtaReuniaoPDFExportView.as_view(), name='exportar_pdf'),
    path('exportar-excel/', AtaReuniaoExcelExportView.as_view(), name='exportar_excel'),
]
