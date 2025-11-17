
from django.urls import path
from . import views

# Define o namespace da app, para podermos usar {% url 'documentos:lista' %}
app_name = 'documentos' 

urlpatterns = [
    # 1. Dashboard de Documentos (Lista principal)
    # ex: /documentos/
    path('', views.DocumentoListView.as_view(), name='lista'),

    # 2. Adicionar Documento (anexado a um objeto genérico)
    # ex: /documentos/adicionar/15/42/ (ContentType 15, Objeto 42)
    path(
        'adicionar/<int:ct_id>/<int:obj_id>/', 
        views.DocumentoCreateView.as_view(), 
        name='adicionar'
    ),

    # 3. Download Seguro
    # ex: /documentos/5/download/
    path(
        '<int:pk>/download/', 
        views.DocumentoDownloadView.as_view(), 
        name='download'
    ),

    # 4. Renovar Documento (substitui o <pk>)
    # ex: /documentos/5/renovar/
    path(
        '<int:pk>/renovar/', 
        views.DocumentoRenewView.as_view(), 
        name='renovar'
    ),

    # 5. Deletar Documento
    # ex: /documentos/5/deletar/
    path(
        '<int:pk>/deletar/', 
        views.DocumentoDeleteView.as_view(), 
        name='deletar'
    ),
]
