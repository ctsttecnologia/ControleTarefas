from django.urls import path
from .views import (
    AtaReuniaoListView, AtaReuniaoCreateView, 
    AtaReuniaoUpdateView, AtaReuniaoDeleteView,
    exportar_pdf, exportar_excel
)

urlpatterns = [
    path('', AtaReuniaoListView.as_view(), name='ata_reuniao_list'),
    path('novo/', AtaReuniaoCreateView.as_view(), name='ata_reuniao_create'),
    path('editar/<int:pk>/', AtaReuniaoUpdateView.as_view(), name='ata_reuniao_update'),
    path('excluir/<int:pk>/', AtaReuniaoDeleteView.as_view(), name='ata_reuniao_delete'),
    path('exportar-pdf/', exportar_pdf, name='exportar_pdf'),
    path('exportar-excel/', exportar_excel, name='exportar_excel'),
]


