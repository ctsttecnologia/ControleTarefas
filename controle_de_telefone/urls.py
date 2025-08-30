# controle_telefones/urls.py

from django.urls import path
from . import views

app_name = 'controle_de_telefone'

urlpatterns = [
    # Rota principal do app
    path('', views.DashboardView.as_view(), name='dashboard'), 
    # URLs do CRUD de Aparelhos
    path('aparelhos/', views.AparelhoListView.as_view(), name='aparelho_list'),
    path('aparelhos/novo/', views.AparelhoCreateView.as_view(), name='aparelho_create'),
    path('aparelhos/<int:pk>/', views.AparelhoDetailView.as_view(), name='aparelho_detail'),
    path('aparelhos/<int:pk>/editar/', views.AparelhoUpdateView.as_view(), name='aparelho_update'),
    path('aparelhos/<int:pk>/deletar/', views.AparelhoDeleteView.as_view(), name='aparelho_delete'),
    path('aparelhos/', views.AparelhoListView.as_view(), name='aparelho_list'),
    path('aparelhos/novo/', views.AparelhoCreateView.as_view(), name='aparelho_create'),

    # URLs do CRUD de Marcas
    path('marcas/', views.MarcaListView.as_view(), name='marca_list'),
    path('marcas/nova/', views.MarcaCreateView.as_view(), name='marca_create'),
    path('marcas/<int:pk>/editar/', views.MarcaUpdateView.as_view(), name='marca_update'),
    path('marcas/<int:pk>/deletar/', views.MarcaDeleteView.as_view(), name='marca_delete'),

    # URLs do CRUD de Modelos
    path('modelos/', views.ModeloListView.as_view(), name='modelo_list'),
    path('modelos/novo/', views.ModeloCreateView.as_view(), name='modelo_create'),
    path('modelos/<int:pk>/editar/', views.ModeloUpdateView.as_view(), name='modelo_update'),
    path('modelos/<int:pk>/deletar/', views.ModeloDeleteView.as_view(), name='modelo_delete'),

    # URLs do CRUD de Linhas Telefônicas
    path('linhas/', views.LinhaTelefonicaListView.as_view(), name='linhatelefonica_list'),
    path('linhas/nova/', views.LinhaTelefonicaCreateView.as_view(), name='linhatelefonica_create'),
    path('linhas/<int:pk>/editar/', views.LinhaTelefonicaUpdateView.as_view(), name='linhatelefonica_update'),
    path('linhas/<int:pk>/deletar/', views.LinhaTelefonicaDeleteView.as_view(), name='linhatelefonica_delete'),
    path('linhas/', views.LinhaTelefonicaListView.as_view(), name='linhatelefonica_list'),
    path('linhas/<int:pk>/', views.LinhaTelefonicaDetailView.as_view(), name='linhatelefonica_detail'), 
    path('linhas/nova/', views.LinhaTelefonicaCreateView.as_view(), name='linhatelefonica_create'),
    path('linhas/<int:pk>/editar/', views.LinhaTelefonicaUpdateView.as_view(), name='linhatelefonica_update'),
    path('linhas/<int:pk>/excluir/', views.LinhaTelefonicaDeleteView.as_view(), name='linhatelefonica_delete'),

    # URLs do CRUD de Vínculos
    path('vinculos/', views.VinculoListView.as_view(), name='vinculo_list'),
    path('vinculos/novo/', views.VinculoCreateView.as_view(), name='vinculo_create'),
    path('vinculos/<int:pk>/', views.VinculoDetailView.as_view(), name='vinculo_detail'),
    path('vinculos/<int:pk>/editar/', views.VinculoUpdateView.as_view(), name='vinculo_update'),
    path('vinculos/<int:pk>/deletar/', views.VinculoDeleteView.as_view(), name='vinculo_delete'),

    # URLs do CRUD de Operadoras
    path('operadoras/', views.OperadoraListView.as_view(), name='operadora_list'),
    path('operadoras/nova/', views.OperadoraCreateView.as_view(), name='operadora_create'),
    path('operadoras/<int:pk>/editar/', views.OperadoraUpdateView.as_view(), name='operadora_update'),
    path('operadoras/<int:pk>/deletar/', views.OperadoraDeleteView.as_view(), name='operadora_delete'),

    # URLs do CRUD de Planos
    path('planos/', views.PlanoListView.as_view(), name='plano_list'),
    path('planos/novo/', views.PlanoCreateView.as_view(), name='plano_create'),
    path('planos/<int:pk>/editar/', views.PlanoUpdateView.as_view(), name='plano_update'),
    path('planos/<int:pk>/deletar/', views.PlanoDeleteView.as_view(), name='plano_delete'),
    
    # URL de download
    path('vinculos/<int:vinculo_id>/download/', views.download_termo, name='download_termo'),
]


