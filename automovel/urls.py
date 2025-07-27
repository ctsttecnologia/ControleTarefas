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
    path('checklists/<int:pk>/export/word/', views.ChecklistExportWordView.as_view(), name='checklist_export_word'),
    # Relatórios
    path('relatorios/carros/<str:format>/', views.CarroReportView.as_view(), name='relatorio_carros'),

    # Calendário
    path('calendario/', views.CalendarioView.as_view(), name='calendario'),

    # APIs
    path('api/carros-disponiveis/', views.CarrosDisponiveisAPIView.as_view(), name='api_carros_disponiveis'),
    path('api/proxima-manutencao/', views.ProximaManutencaoAPIView.as_view(), name='api_proxima_manutencao'),
    path('api/agendamentos/', views.CalendarioAPIView.as_view(), name='api_agendamentos'),


]
