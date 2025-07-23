# seguranca_trabalho/urls.py# seguranca_trabalho/urls.py

from django.urls import path

# Importando todas as views necessárias para um CRUD completo e ações.
from .views import (
    # Dashboards
    ControleEPIPorFuncaoView,
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
    FichaEPIDeleteView,
    FichaEPIUpdateView,
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
    GerarFichaPDFView,
    RegistrarDevolucaoView,
    RelatorioSSTPDFView,
)

# O app_name é crucial para o namespacing das URLs.
app_name = 'seguranca_trabalho'

urlpatterns = [
    # ========================================================================
    # DASHBOARD
    # ========================================================================
    # URL principal do módulo de SST.
    path('', DashboardSSTView.as_view(), name='dashboard'),
    path('relatório',RelatorioSSTPDFView.as_view(), name='relatorio_pdf_template'),

    # ========================================================================
    # FICHAS DE EPI E ENTREGAS
    # ========================================================================
    # Gerenciamento das fichas de EPI dos funcionários.
    path('fichas/', FichaEPIListView.as_view(), name='ficha_list'),
    path('fichas/nova/', FichaEPICreateView.as_view(), name='ficha_create'),
    path('fichas/<int:pk>/', FichaEPIDetailView.as_view(), name='ficha_detail'),
    path('controle-epi-funcao/', ControleEPIPorFuncaoView.as_view(), name='controle_epi_por_funcao'),  

    # Ações relacionadas a uma entrega de EPI específica.
    path('fichas/<int:ficha_pk>/adicionar-entrega/', AdicionarEntregaView.as_view(), name='entrega_create'),
    path('entregas/<int:pk>/assinar/', AssinarEntregaView.as_view(), name='entrega_sign'),
    path('entregas/<int:pk>/devolver/', RegistrarDevolucaoView.as_view(), name='entrega_return'),
    path('fichas/<int:pk>/update/', FichaEPIUpdateView.as_view(), name='ficha_update'),
    path('fichas/<int:pk>/delete/', FichaEPIDeleteView.as_view(), name='ficha_delete'),
    path('fichas/<int:pk>/pdf/', GerarFichaPDFView.as_view(), name='ficha_pdf'),

    # ========================================================================
    # CATÁLOGOS (Equipamentos, Fabricantes, Fornecedores)
    # ========================================================================

    # --- CRUD de Equipamentos ---
    path('equipamentos/', EquipamentoListView.as_view(), name='equipamento_list'),
    path('equipamentos/novo/', EquipamentoCreateView.as_view(), name='equipamento_create'),
    path('equipamentos/<int:pk>/', EquipamentoDetailView.as_view(), name='equipamento_detail'),
    path('equipamentos/<int:pk>/editar/', EquipamentoUpdateView.as_view(), name='equipamento_update'),
    path('equipamentos/<int:pk>/excluir/', EquipamentoDeleteView.as_view(), name='equipamento_delete'),

    # --- CRUD de Fabricantes ---
    # (Supondo que FabricanteDeleteView será criada seguindo o padrão das outras)
    path('fabricantes/', FabricanteListView.as_view(), name='fabricante_list'),
    path('fabricantes/novo/', FabricanteCreateView.as_view(), name='fabricante_create'),
    path('fabricantes/<int:pk>/', FabricanteDetailView.as_view(), name='fabricante_detail'),
    path('fabricantes/<int:pk>/editar/', FabricanteUpdateView.as_view(), name='fabricante_update'),
    # path('catalogo/fabricantes/<int:pk>/excluir/', FabricanteDeleteView.as_view(), name='fabricante_delete'),

    # --- CRUD de Fornecedores ---
    # (Supondo que FornecedorDeleteView será criada seguindo o padrão das outras)
    path('fornecedores/', FornecedorListView.as_view(), name='fornecedor_list'),
    path('fornecedores/novo/', FornecedorCreateView.as_view(), name='fornecedor_create'),
    path('fornecedores/<int:pk>/', FornecedorDetailView.as_view(), name='fornecedor_detail'),
    path('fornecedores/<int:pk>/editar/', FornecedorUpdateView.as_view(), name='fornecedor_update'),
    # path('catalogo/fornecedores/<int:pk>/excluir/', FornecedorDeleteView.as_view(), name='fornecedor_delete'),
]

