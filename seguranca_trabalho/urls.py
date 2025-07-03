# seguranca_trabalho/urls.py (NOVO)

from django.urls import path
from . import views 

app_name = 'seguranca_trabalho'

urlpatterns = [
    path('', views.DashboardSSTView.as_view(), name='dashboard'),
    
    # Fichas de EPI
    path('fichas/', views.FichaEPIListView.as_view(), name='ficha_lista'),
    path('fichas/nova/', views.FichaEPICreateView.as_view(), name='ficha_criar_form'),
    path('fichas/<int:pk>/', views.FichaEPIDetailView.as_view(), name='ficha_detalhe'),
    path('fichas/<int:pk>/gerar-relatorio/', views.gerar_relatorio_ficha, name='gerar_relatorio'),
    
    # Entregas e Assinaturas
    path('fichas/<int:ficha_pk>/adicionar-entrega/', views.adicionar_entrega, name='adicionar_entrega'),
    path('entregas/<int:pk>/assinar-recebimento/', views.assinar_entrega_recebimento, name='assinar_recebimento'),
    path('entregas/<int:pk>/registrar-devolucao/', views.registrar_devolucao, name='registrar_devolucao'),

    path('equipamentos/', views.EquipamentoListView.as_view(), name='equipamento_list'),
    path('equipamentos/novo/', views.EquipamentoCreateView.as_view(), name='equipamento_create'),
    path('equipamentos/editar/<int:pk>/', views.EquipamentoUpdateView.as_view(), name='equipamento_update'),
]