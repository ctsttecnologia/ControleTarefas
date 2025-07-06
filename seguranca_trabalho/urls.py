# seguranca_trabalho/urls.py

from django.urls import path
from .views import (
    DashboardSSTView,
    EquipamentoListView, EquipamentoCreateView, EquipamentoUpdateView, 
    EquipamentoDetailView, EquipamentoDeleteView,
    FabricanteListView, FabricanteCreateView, FabricanteUpdateView,
    FornecedorListView, FornecedorCreateView, FornecedorUpdateView,
    FichaEPIListView, FichaEPICreateView, FichaEPIDetailView,
    AdicionarEntregaView, AssinarEntregaView, RegistrarDevolucaoView,
    FuncaoDoColaboradorAPIView,
)

app_name = 'seguranca_trabalho'

urlpatterns = [
    # Dashboard
    path('', DashboardSSTView.as_view(), name='dashboard'),
    
    # CRUD de Fichas de EPI
    path('fichas/', FichaEPIListView.as_view(), name='ficha_lista'),
    path('fichas/nova/', FichaEPICreateView.as_view(), name='ficha_criar'),
    path('fichas/<int:pk>/', FichaEPIDetailView.as_view(), name='ficha_detalhe'),
    
    # Ações dentro de uma Ficha
    path('fichas/<int:ficha_pk>/adicionar-entrega/', AdicionarEntregaView.as_view(), name='adicionar_entrega'),
    path('entregas/<int:pk>/assinar/', AssinarEntregaView.as_view(), name='assinar_entrega'),
    path('entregas/<int:pk>/devolver/', RegistrarDevolucaoView.as_view(), name='registrar_devolucao'),

    # CRUD de Equipamentos
    path('equipamentos/', EquipamentoListView.as_view(), name='equipamento_list'),
    path('equipamentos/novo/', EquipamentoCreateView.as_view(), name='equipamento_create'),
    path('equipamentos/<int:pk>/', EquipamentoDetailView.as_view(), name='equipamento_detail'),
    path('equipamentos/<int:pk>/editar/', EquipamentoUpdateView.as_view(), name='equipamento_update'),
    path('equipamentos/<int:pk>/excluir/', EquipamentoDeleteView.as_view(), name='equipamento_delete'),

    # CRUD de Fabricantes
    path('fabricantes/', FabricanteListView.as_view(), name='fabricante_list'),
    path('fabricantes/novo/', FabricanteCreateView.as_view(), name='fabricante_create'),
    path('fabricantes/<int:pk>/editar/', FabricanteUpdateView.as_view(), name='fabricante_update'),
    
    # CRUD de Fornecedores
    path('fornecedores/', FornecedorListView.as_view(), name='fornecedor_list'),
    path('fornecedores/novo/', FornecedorCreateView.as_view(), name='fornecedor_create'),
    path('fornecedores/<int:pk>/editar/', FornecedorUpdateView.as_view(), name='fornecedor_update'),

    # API
    path('api/get-funcao-colaborador/<int:colaborador_id>/', FuncaoDoColaboradorAPIView.as_view(), name='api_get_funcao_colaborador'),
]