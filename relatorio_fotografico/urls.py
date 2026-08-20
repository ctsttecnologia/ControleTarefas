# relatorio_fotografico/urls.py
from django.urls import path
from . import views

app_name = 'relatorio_fotografico'

urlpatterns = [
    path('', views.RelatorioListView.as_view(), name='list'),
    path('novo/', views.RelatorioCreateView.as_view(), name='create'),
    path('<int:pk>/', views.RelatorioDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.RelatorioUpdateView.as_view(), name='update'),
    path('<int:pk>/excluir/', views.RelatorioDeleteView.as_view(), name='delete'),

    path('<int:pk>/fotos/upload/', views.FotoUploadView.as_view(), name='foto_upload'),
    path('<int:pk>/fotos/reordenar/', views.FotoReorderView.as_view(), name='foto_reorder'),
    path('foto/<int:pk>/editar/', views.FotoUpdateView.as_view(), name='foto_update'),
    path('foto/<int:pk>/excluir/', views.FotoDeleteView.as_view(), name='foto_delete'),

    path('<int:pk>/exportar/docx/', views.RelatorioExportDocxView.as_view(), name='export_docx'),
    path('<int:pk>/exportar/pdf/', views.RelatorioExportPdfView.as_view(), name='export_pdf'),
]


