
# documentos/urls.py

from django.urls import path
from . import views

app_name = 'documentos'

urlpatterns = [
    # Dashboard principal
    path('', views.DocumentoListView.as_view(), name='lista'),

    # CRUD
    path('adicionar/<int:ct_id>/<int:obj_id>/', views.DocumentoCreateView.as_view(), name='adicionar'),
    path('<int:pk>/download/', views.DocumentoDownloadView.as_view(), name='download'),
    path('<int:pk>/renovar/', views.DocumentoRenewView.as_view(), name='renovar'),
    path('<int:pk>/deletar/', views.DocumentoDeleteView.as_view(), name='deletar'),
]
