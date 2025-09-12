# controle_de_telefone/urls.py

from django.urls import path
from . import views

# Importe as novas classes de view
from .views import (
    AparelhoListView, AparelhoDetailView, AparelhoCreateView, AparelhoUpdateView, AparelhoDeleteView, AssinarTermoView,
    LinhaTelefonicaListView, LinhaTelefonicaDetailView, LinhaTelefonicaCreateView, LinhaTelefonicaUpdateView, LinhaTelefonicaDeleteView,
    VinculoListView, VinculoDetailView, VinculoCreateView, VinculoUpdateView, VinculoDeleteView,
    MarcaListView, MarcaCreateView, MarcaUpdateView, MarcaDeleteView,
    ModeloListView, ModeloCreateView, ModeloUpdateView, ModeloDeleteView,
    OperadoraListView, OperadoraCreateView, OperadoraUpdateView, OperadoraDeleteView,
    PlanoListView, PlanoCreateView, PlanoUpdateView, PlanoDeleteView,
    DashboardView, DownloadTermoView, RegenerarTermoView, NotificarAssinaturaView, 
)

app_name = 'controle_de_telefone'

urlpatterns = [
    # Dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    # Aparelhos
    path('aparelhos/', AparelhoListView.as_view(), name='aparelho_list'),
    path('aparelhos/novo/', AparelhoCreateView.as_view(), name='aparelho_create'),
    path('aparelhos/<int:pk>/', AparelhoDetailView.as_view(), name='aparelho_detail'),
    path('aparelhos/<int:pk>/editar/', AparelhoUpdateView.as_view(), name='aparelho_update'),
    path('aparelhos/<int:pk>/excluir/', AparelhoDeleteView.as_view(), name='aparelho_delete'),

    # Linhas Telefônicas
    path('linhas/', LinhaTelefonicaListView.as_view(), name='linhatelefonica_list'),
    path('linhas/nova/', LinhaTelefonicaCreateView.as_view(), name='linhatelefonica_create'),
    path('linhas/<int:pk>/', LinhaTelefonicaDetailView.as_view(), name='linhatelefonica_detail'),
    path('linhas/<int:pk>/editar/', LinhaTelefonicaUpdateView.as_view(), name='linhatelefonica_update'),
    path('linhas/<int:pk>/excluir/', LinhaTelefonicaDeleteView.as_view(), name='linhatelefonica_delete'),

    # Vínculos
    path('vinculos/', VinculoListView.as_view(), name='vinculo_list'),
    path('vinculos/novo/', VinculoCreateView.as_view(), name='vinculo_create'),
    path('vinculos/<int:pk>/', VinculoDetailView.as_view(), name='vinculo_detail'),
    path('vinculos/<int:pk>/editar/', VinculoUpdateView.as_view(), name='vinculo_update'),
    path('vinculos/<int:pk>/excluir/', VinculoDeleteView.as_view(), name='vinculo_delete'),

    path('vinculos/<int:pk>/download/', DownloadTermoView.as_view(), name='download_termo'),
    path('vinculos/<int:pk>/regenerar-termo/', RegenerarTermoView.as_view(), name='regenerar_termo'),
    path('vinculos/<int:pk>/notificar/', NotificarAssinaturaView.as_view(), name='notificar_assinatura'),
    path('vinculos/assinar/<int:pk>/', AssinarTermoView.as_view(), name='vinculo_assinar'), 
    # Marcas
    path('marcas/', MarcaListView.as_view(), name='marca_list'),
    path('marcas/nova/', MarcaCreateView.as_view(), name='marca_create'),
    path('marcas/<int:pk>/editar/', MarcaUpdateView.as_view(), name='marca_update'),
    path('marcas/<int:pk>/excluir/', MarcaDeleteView.as_view(), name='marca_delete'),

    # Modelos
    path('modelos/', ModeloListView.as_view(), name='modelo_list'),
    path('modelos/novo/', ModeloCreateView.as_view(), name='modelo_create'),
    path('modelos/<int:pk>/editar/', ModeloUpdateView.as_view(), name='modelo_update'),
    path('modelos/<int:pk>/excluir/', ModeloDeleteView.as_view(), name='modelo_delete'),
    
    # Operadoras
    path('operadoras/', OperadoraListView.as_view(), name='operadora_list'),
    path('operadoras/nova/', OperadoraCreateView.as_view(), name='operadora_create'),
    path('operadoras/<int:pk>/editar/', OperadoraUpdateView.as_view(), name='operadora_update'),
    path('operadoras/<int:pk>/excluir/', OperadoraDeleteView.as_view(), name='operadora_delete'),
    
    # Planos
    path('planos/', PlanoListView.as_view(), name='plano_list'),
    path('planos/novo/', PlanoCreateView.as_view(), name='plano_create'),
    path('planos/<int:pk>/editar/', PlanoUpdateView.as_view(), name='plano_update'),
    path('planos/<int:pk>/excluir/', PlanoDeleteView.as_view(), name='plano_delete'),


]


