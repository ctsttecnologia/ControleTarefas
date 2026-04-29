# seguranca_trabalho/urls.py
"""
URLs do módulo de Segurança do Trabalho (SST).

Organização:
    - Dashboard e relatórios
    - Fichas de EPI (CRUD + ações)
    - Entregas (assinatura, devolução)
    - Equipamentos (CRUD + ajuste de estoque)
    - Funções (CRUD)
    - Associações Cargo↔Função
"""
from django.urls import path

from .views import (
    # Dashboard e relatórios
    DashboardSSTView,
    RelatorioSSTPDFView,
    ControleEPIPorFuncaoView,

    # Fichas de EPI (CRUD)
    FichaEPIListView,
    FichaEPICreateView,
    FichaEPIDetailView,
    FichaEPIUpdateView,
    FichaEPIDeleteView,
    GerarFichaPDFView,
    minha_ficha_redirect_view,

    # Entregas e assinaturas
    AssinarEntregaView,
    AssinarTermoView,
    RegistrarDevolucaoView,

    # Equipamentos (CRUD)
    EquipamentoListView,
    EquipamentoDetailView,
    EquipamentoCreateView,
    EquipamentoUpdateView,
    EquipamentoDeleteView,
    AjusteEstoqueView,

    # Funções (CRUD)
    FuncaoListView,
    FuncaoCreateView,
    FuncaoUpdateView,
    FuncaoDeleteView,

    # Associações Cargo↔Função
    AssociacaoListView,
    AssociacaoCreateView,
    desvincular_funcao_cargo,
)

app_name = 'seguranca_trabalho'

urlpatterns = [
    # ═══════════════════════════════════════════════════════════
    # 📊 DASHBOARD E RELATÓRIOS
    # ═══════════════════════════════════════════════════════════
    path('', DashboardSSTView.as_view(), name='dashboard'),
    path('relatorio/', RelatorioSSTPDFView.as_view(), name='relatorio_pdf_template'),
    path('controle-epi-funcao/', ControleEPIPorFuncaoView.as_view(), name='controle_epi_por_funcao'),

    # ═══════════════════════════════════════════════════════════
    # 📋 FICHAS DE EPI (CRUD + AÇÕES)
    # ═══════════════════════════════════════════════════════════
    path('fichas/', FichaEPIListView.as_view(), name='ficha_list'),
    path('fichas/nova/', FichaEPICreateView.as_view(), name='ficha_create'),
    path('fichas/<int:pk>/', FichaEPIDetailView.as_view(), name='ficha_detail'),
    path('fichas/<int:pk>/update/', FichaEPIUpdateView.as_view(), name='ficha_update'),
    path('fichas/<int:pk>/delete/', FichaEPIDeleteView.as_view(), name='ficha_delete'),
    path('fichas/<int:pk>/pdf/', GerarFichaPDFView.as_view(), name='ficha_pdf_template'),
    path('ficha/<int:pk>/assinar-termo/', AssinarTermoView.as_view(), name='assinar_termo'),
    path('minha-ficha/', minha_ficha_redirect_view, name='minha_ficha_redirect'),

    # ═══════════════════════════════════════════════════════════
    # 📦 ENTREGAS DE EPI (ASSINATURA E DEVOLUÇÃO)
    # ═══════════════════════════════════════════════════════════
    path('entregas/<int:pk>/assinar/', AssinarEntregaView.as_view(), name='entrega_sign'),
    path('entregas/<int:pk>/devolver/', RegistrarDevolucaoView.as_view(), name='entrega_return'),

    # ═══════════════════════════════════════════════════════════
    # 🦺 EQUIPAMENTOS (EPI) — CRUD + ESTOQUE
    # ═══════════════════════════════════════════════════════════
    path('equipamentos/', EquipamentoListView.as_view(), name='equipamento_list'),
    path('equipamentos/novo/', EquipamentoCreateView.as_view(), name='equipamento_create'),
    path('equipamentos/<int:pk>/', EquipamentoDetailView.as_view(), name='equipamento_detail'),
    path('equipamentos/<int:pk>/editar/', EquipamentoUpdateView.as_view(), name='equipamento_update'),
    path('equipamentos/<int:pk>/excluir/', EquipamentoDeleteView.as_view(), name='equipamento_delete'),
    path('equipamentos/<int:pk>/ajuste-estoque/', AjusteEstoqueView.as_view(), name='ajuste_estoque'),

    # ═══════════════════════════════════════════════════════════
    # 👷 FUNÇÕES — CRUD
    # ═══════════════════════════════════════════════════════════
    path('funcoes/', FuncaoListView.as_view(), name='funcao_list'),
    path('funcoes/nova/', FuncaoCreateView.as_view(), name='funcao_create'),
    path('funcoes/<int:pk>/editar/', FuncaoUpdateView.as_view(), name='funcao_update'),
    path('funcoes/<int:pk>/excluir/', FuncaoDeleteView.as_view(), name='funcao_delete'),

    # ═══════════════════════════════════════════════════════════
    # 🔗 ASSOCIAÇÕES CARGO ↔ FUNÇÃO
    # ═══════════════════════════════════════════════════════════
    path('associacoes/', AssociacaoListView.as_view(), name='lista_associacoes'),
    path('associar/', AssociacaoCreateView.as_view(), name='associar_funcao_cargo'),
    path('funcao/<int:funcao_id>/desvincular/<int:cargo_id>/', desvincular_funcao_cargo, name='desvincular_funcao_cargo',),
]



