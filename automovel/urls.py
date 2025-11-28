# automovel/urls.py

from django.urls import path
from . import views

app_name = 'automovel'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    # Carros
    path('carros/', views.CarroListView.as_view(), name='carro_list'),
    path('carros/novo/', views.CarroCreateView.as_view(), name='carro_create'),
    path('carros/<int:pk>/', views.CarroDetailView.as_view(), name='carro_detail'),
    path('carros/<int:pk>/editar/', views.CarroUpdateView.as_view(), name='carro_update'),
    # Agendamentos
    path('agendamentos/', views.AgendamentoListView.as_view(), name='agendamento_list'),
    path('agendamentos/novo/', views.AgendamentoCreateView.as_view(), name='agendamento_create'),
    path('agendamentos/<int:pk>/', views.AgendamentoDetailView.as_view(), name='agendamento_detail'),
    path('agendamentos/<int:pk>/editar/', views.AgendamentoUpdateView.as_view(), name='agendamento_update'),
    # Checklists
    path('agendamentos/<int:agendamento_pk>/checklist/novo/', views.ChecklistCreateView.as_view(), name='checklist_create'),
    # NOVA ROTA para ver os detalhes de um checklist preenchido
    path('checklists/<int:pk>/', views.ChecklistDetailView.as_view(), name='checklist_detail'),
    # URL para EDITAR um checklist existente
    path('agendamentos/checklist/<int:pk>/editar/', views.ChecklistUpdateView.as_view(), name='checklist_update'),
    # URL para CRIAR um novo checklist para um agendamento
    path('agendamentos/<int:agendamento_pk>/checklist/novo/', views.ChecklistCreateView.as_view(), name='checklist_create'),
    # Relatórios
    path('relatorios/excel/<str:tipo>/', views.gerar_relatorio_excel,  name='gerar_relatorio_excel'),
    path('relatorios/word/<str:tipo>/<int:pk>/',  views.gerar_relatorio_word,  name='gerar_relatorio_word'),
    # Calendário
    path('calendario/', views.CalendarioView.as_view(), name='calendario'),
    # APIs
    path('api/carros-disponiveis/', views.CarrosDisponiveisAPIView.as_view(), name='api_carros_disponiveis'),
    path('api/proxima-manutencao/', views.ProximaManutencaoAPIView.as_view(), name='api_proxima_manutencao'),
    path('api/agendamentos/', views.CalendarioAPIView.as_view(), name='api_agendamentos'),
    # Rastreamento
    path('rastreamento/create/', views.RastreamentoCreateView.as_view(), name='rastreamento_create'),
    path('agendamento/<int:pk>/mapa/', views.RastreamentoMapView.as_view(), name='rastreamento_map'),
    path('api/rastreamento/receber/', views.RastreamentoAPIView.as_view(), name='api_rastreamento_receber'),
    path('carro/<int:pk>/agendar-manutencao/', views.AgendarManutencaoView.as_view(), name='agendar_manutencao'),
    path('manutencoes/', views.ManutencaoListView.as_view(), name='manutencao_list'),
    # Rota para EDITAR Manutenção (Ação do Modal)
    path('manutencao/<int:pk>/editar/', views.ManutencaoUpdateView.as_view(), name='manutencao_update'),
    # Rota para FINALIZAR Agendamento (Ação do Modal)
    path('agendamentos/<int:pk>/finalizar/', views.AgendamentoFinalizarView.as_view(), name='agendamento_finalizar'),


]
