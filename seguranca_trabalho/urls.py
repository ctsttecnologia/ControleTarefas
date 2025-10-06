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
 
    FichaEPIDeleteView,
    FichaEPIUpdateView,
    # A view FabricanteDeleteView precisa ser criada se a funcionalidade for desejada.
   
    # Fichas de EPI e Ações relacionadas
    FichaEPIListView,
    FichaEPICreateView,
    FichaEPIDetailView,
    #AdicionarEntregaView,
    AssinarEntregaView,
    FuncaoCreateView,
    FuncaoDeleteView,
    FuncaoListView,
    FuncaoUpdateView,
    GerarFichaPDFView,
    RegistrarDevolucaoView,
    RelatorioSSTPDFView,
    minha_ficha_redirect_view,
)

# O app_name é crucial para o namespacing das URLs.
app_name = 'seguranca_trabalho'

urlpatterns = [

    # URL principal do módulo de SST.
    path('', DashboardSSTView.as_view(), name='dashboard'),
    path('relatório',RelatorioSSTPDFView.as_view(), name='relatorio_pdf_template'),

    # Gerenciamento das fichas de EPI dos funcionários.
    path('fichas/', FichaEPIListView.as_view(), name='ficha_list'),
    path('fichas/nova/', FichaEPICreateView.as_view(), name='ficha_create'),
    path('fichas/<int:pk>/', FichaEPIDetailView.as_view(), name='ficha_detail'),
    path('controle-epi-funcao/', ControleEPIPorFuncaoView.as_view(), name='controle_epi_por_funcao'),
    path('entregas/<int:pk>/assinar/', AssinarEntregaView.as_view(), name='entrega_sign'),

    path('funcoes/', FuncaoListView.as_view(), name='funcao_list'),
    path('funcoes/nova/', FuncaoCreateView.as_view(), name='funcao_create'),
    path('funcoes/<int:pk>/editar/', FuncaoUpdateView.as_view(), name='funcao_update'),
    path('funcoes/<int:pk>/excluir/', FuncaoDeleteView.as_view(), name='funcao_delete'),
    
    path('entregas/<int:pk>/assinar/', AssinarEntregaView.as_view(), name='captura_teste'),
    path('entregas/<int:pk>/devolver/', RegistrarDevolucaoView.as_view(), name='entrega_return'),
    path('fichas/<int:pk>/update/', FichaEPIUpdateView.as_view(), name='ficha_update'),
    path('fichas/<int:pk>/delete/', FichaEPIDeleteView.as_view(), name='ficha_delete'),
    path('fichas/<int:pk>/pdf/', GerarFichaPDFView.as_view(), name='ficha_pdf_template'),
    path('minha-ficha/', minha_ficha_redirect_view, name='minha_ficha'),

    # --- CRUD de Equipamentos ---
    path('equipamentos/', EquipamentoListView.as_view(), name='equipamento_list'),
    path('equipamentos/novo/', EquipamentoCreateView.as_view(), name='equipamento_create'),
    path('equipamentos/<int:pk>/', EquipamentoDetailView.as_view(), name='equipamento_detail'),
    path('equipamentos/<int:pk>/editar/', EquipamentoUpdateView.as_view(), name='equipamento_update'),
    path('equipamentos/<int:pk>/excluir/', EquipamentoDeleteView.as_view(), name='equipamento_delete'),

]

