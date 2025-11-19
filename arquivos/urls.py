
from django.urls import path
from . import views

app_name = 'arquivos'

urlpatterns = [
    path('', views.ArquivoListView.as_view(), name='lista_documentos'), # Se aqui for 'lista_documentos', a view deve usar 'lista_documentos'
    path('novo/', views.ArquivoCreateView.as_view(), name='criar_documento'),
    path('editar/<int:pk>/', views.ArquivoUpdateView.as_view(), name='editar_documento'),
    path('excluir/<int:pk>/', views.ArquivoDeleteView.as_view(), name='excluir_documento'),
]
