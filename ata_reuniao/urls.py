# ata_reuniao/urls.py

from django.urls import path
from .views import (
    AtaReuniaoListView, AtaReuniaoCreateView, AtaReuniaoUpdateView,
    AtaReuniaoDeleteView, AtaReuniaoDashboardView, AtaReuniaoPDFExportView,
    AtaReuniaoExcelExportView, AtaReuniaoDetailView, AtaReuniaoAddCommentView, UpdateTaskStatusView # Adicionado DetailView
)

app_name = 'ata_reuniao'

urlpatterns = [
    # --- Rota Principal e Dashboard ---
    path('', AtaReuniaoListView.as_view(), name='ata_reuniao_list'),
    path('dashboard/', AtaReuniaoDashboardView.as_view(), name='ata_reuniao_dashboard'),

    # --- Rotas de CRUD para Atas ---
    path('ata/nova/', AtaReuniaoCreateView.as_view(), name='ata_reuniao_create'),
    path('ata/<int:pk>/', AtaReuniaoDetailView.as_view(), name='ata_reuniao_detail'),
    path('ata/<int:pk>/editar/', AtaReuniaoUpdateView.as_view(), name='ata_reuniao_update'),
    path('ata/<int:pk>/excluir/', AtaReuniaoDeleteView.as_view(), name='ata_confirm_delete'),
    path('ata/<int:pk>/add_comment/', AtaReuniaoAddCommentView.as_view(), name='ata_add_comment'),


    # --- Rotas de Exportação ---
    # Usam a lista principal de atas como base
    path('exportar/pdf/', AtaReuniaoPDFExportView.as_view(), name='ata_reuniao_export_pdf'),
    path('exportar/excel/', AtaReuniaoExcelExportView.as_view(), name='ata_reuniao_export_excel'),


    # NOVO ENDPOINT PARA O DRAG AND DROP
    path('api/update-status/<int:pk>/', UpdateTaskStatusView.as_view(), name='api_update_status'),
]


