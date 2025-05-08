
from django.urls import path
from . import views

app_name = 'automovel'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Carros
    path('carros/', views.CarroListView.as_view(), name='carro_list'),
    path('carros/novo/', views.CarroCreateView.as_view(), name='carro_create'),
    path('carros/<int:pk>/editar/', views.CarroUpdateView.as_view(), name='carro_update'),
    path('carros/<int:pk>/', views.CarroDetailView.as_view(), name='carro_detail'),
    
    # Agendamentos
    path('agendamentos/', views.AgendamentoListView.as_view(), name='agendamento_list'),
    path('agendamentos/novo/', views.AgendamentoCreateView.as_view(), name='agendamento_create'),
    path('agendamentos/<int:pk>/', views.AgendamentoDetailView.as_view(), name='agendamento_detail'),
    path('agendamentos/<int:pk>/editar/', views.AgendamentoUpdateView.as_view(), name='agendamento_update'),
    
    # Checklists
    path('checklists/novo/', views.ChecklistCreateView.as_view(), name='checklist_create'),
    
    # Relatórios
    path('relatorios/carros/<str:format>/', views.relatorio_carros, name='relatorio_carros'),
    
    # APIs
    path('api/carros-disponiveis/', views.carros_disponiveis, name='api_carros_disponiveis'),
    path('api/proxima-manutencao/', views.proxima_manutencao, name='api_proxima_manutencao'),
]