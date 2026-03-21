
# documentos/urls.py
from django.urls import path
from . import views

app_name = 'documentos'

urlpatterns = [
    # ══════════════════════════════════════════════
    # DASHBOARD / LISTA PRINCIPAL (substitui ambas as listas)
    # ══════════════════════════════════════════════
    path('', views.DocumentoListView.as_view(), name='lista'),

    # ══════════════════════════════════════════════
    # DOCUMENTOS AVULSOS (ex-Arquivos: contratos, alvarás, etc.)
    # ══════════════════════════════════════════════
    path('novo/', views.DocumentoEmpresaCreateView.as_view(), name='criar'),
    path('<int:pk>/editar/', views.DocumentoEmpresaUpdateView.as_view(), name='editar'),

    # ══════════════════════════════════════════════
    # DOCUMENTOS ANEXADOS (a Funcionário, Treinamento, etc.)
    # ══════════════════════════════════════════════
    path('adicionar/<int:ct_id>/<int:obj_id>/', views.DocumentoAnexoCreateView.as_view(), name='adicionar'),

    # ══════════════════════════════════════════════
    # AÇÕES COMUNS (download, renovar, excluir)
    # ══════════════════════════════════════════════
    path('<int:pk>/download/', views.DocumentoDownloadView.as_view(), name='download'),
    path('<int:pk>/renovar/', views.DocumentoRenewView.as_view(), name='renovar'),
    path('<int:pk>/excluir/', views.DocumentoDeleteView.as_view(), name='excluir'),
]
