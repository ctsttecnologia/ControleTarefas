# seguranca_trabalho/urls.py# seguranca_trabalho/urls.py

from django.urls import path

# Importando todas as views necessárias para um CRUD completo e ações.
from .views import (
    # Dashboards
    DashboardSSTView,

    # CRUD de Equipamentos
    EquipamentoListView,
    EquipamentoDetailView,
    EquipamentoCreateView,
    EquipamentoUpdateView,
    EquipamentoDeleteView,

    # CRUD de Fabricantes
    FabricanteListView,
    FabricanteDetailView,
    FabricanteCreateView,
    FabricanteUpdateView,
    # A view FabricanteDeleteView precisa ser criada se a funcionalidade for desejada.
    
    # CRUD de Fornecedores
    FornecedorListView,
    FornecedorDetailView,
    FornecedorCreateView,
    FornecedorUpdateView,
    # A view FornecedorDeleteView precisa ser criada se a funcionalidade for desejada.

    # Fichas de EPI e Ações relacionadas
    FichaEPIListView,
    FichaEPICreateView,
    FichaEPIDetailView,
    AdicionarEntregaView,
    AssinarEntregaView,
    RegistrarDevolucaoView,
)

# O app_name é crucial para o namespacing das URLs.
app_name = 'seguranca_trabalho'

urlpatterns = [
    # ========================================================================
    # DASHBOARD
    # ========================================================================
    # URL principal do módulo de SST.
    path('', DashboardSSTView.as_view(), name='dashboard'),


    # ========================================================================
    # FICHAS DE EPI E ENTREGAS
    # ========================================================================
    # Gerenciamento das fichas de EPI dos funcionários.
    path('fichas/', FichaEPIListView.as_view(), name='ficha_list'),
    path('fichas/nova/', FichaEPICreateView.as_view(), name='ficha_create'),
    path('fichas/<int:pk>/', FichaEPIDetailView.as_view(), name='ficha_detail'),
    # Nota: Rotas de Update e Delete para FichaEPI podem ser adicionadas se necessário.
    # path('fichas/<int:pk>/editar/', FichaEPIUpdateView.as_view(), name='ficha_update'),
    # path('fichas/<int:pk>/excluir/', FichaEPIDeleteView.as_view(), name='ficha_delete'),

    # Ações relacionadas a uma entrega de EPI específica.
    path('fichas/<int:ficha_pk>/adicionar-entrega/', AdicionarEntregaView.as_view(), name='entrega_create'),
    path('entregas/<int:pk>/assinar/', AssinarEntregaView.as_view(), name='entrega_sign'),
    path('entregas/<int:pk>/devolver/', RegistrarDevolucaoView.as_view(), name='entrega_return'),


    # ========================================================================
    # CATÁLOGOS (Equipamentos, Fabricantes, Fornecedores)
    # ========================================================================

    # --- CRUD de Equipamentos ---
    path('catalogo/equipamentos/', EquipamentoListView.as_view(), name='equipamento_list'),
    path('catalogo/equipamentos/novo/', EquipamentoCreateView.as_view(), name='equipamento_create'),
    path('catalogo/equipamentos/<int:pk>/', EquipamentoDetailView.as_view(), name='equipamento_detail'),
    path('catalogo/equipamentos/<int:pk>/editar/', EquipamentoUpdateView.as_view(), name='equipamento_update'),
    path('catalogo/equipamentos/<int:pk>/excluir/', EquipamentoDeleteView.as_view(), name='equipamento_delete'),

    # --- CRUD de Fabricantes ---
    # (Supondo que FabricanteDeleteView será criada seguindo o padrão das outras)
    path('catalogo/fabricantes/', FabricanteListView.as_view(), name='fabricante_list'),
    path('catalogo/fabricantes/novo/', FabricanteCreateView.as_view(), name='fabricante_create'),
    path('catalogo/fabricantes/<int:pk>/', FabricanteDetailView.as_view(), name='fabricante_detail'),
    path('catalogo/fabricantes/<int:pk>/editar/', FabricanteUpdateView.as_view(), name='fabricante_update'),
    # path('catalogo/fabricantes/<int:pk>/excluir/', FabricanteDeleteView.as_view(), name='fabricante_delete'),

    # --- CRUD de Fornecedores ---
    # (Supondo que FornecedorDeleteView será criada seguindo o padrão das outras)
    path('catalogo/fornecedores/', FornecedorListView.as_view(), name='fornecedor_list'),
    path('catalogo/fornecedores/novo/', FornecedorCreateView.as_view(), name='fornecedor_create'),
    path('catalogo/fornecedores/<int:pk>/', FornecedorDetailView.as_view(), name='fornecedor_detail'),
    path('catalogo/fornecedores/<int:pk>/editar/', FornecedorUpdateView.as_view(), name='fornecedor_update'),
    # path('catalogo/fornecedores/<int:pk>/excluir/', FornecedorDeleteView.as_view(), name='fornecedor_delete'),
]

