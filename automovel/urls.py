
from . import views
from django.urls import path
from .views import (
    lista_agendamentos, adicionar_agendamento, editar_agendamento,
    excluir_agendamento, AdicionarAssinaturaView, checklist_carro,
    agendamento_fotos, relatorio_checklist_word, relatorio_fotografico_word)


app_name = 'automovel'

urlpatterns = [
    # URLs de Carros
    path('carros/', views.lista_carros, name='lista_carros'),
    path('carros/adicionar/', views.adicionar_carro, name='adicionar_carro'),
    path('carros/editar/<int:pk>/', views.editar_carro, name='editar_carro'),
    path('carros/excluir/<int:pk>/', views.excluir_carro, name='excluir_carro'),
    
    # URLs de Agendamentos
    path('agendamentos/', views.lista_agendamentos, name='lista_agendamentos'),
    path('agendamentos/adicionar/', views.adicionar_agendamento, name='adicionar_agendamento'),
    path('agendamentos/editar/<int:pk>/', views.editar_agendamento, name='editar_agendamento'),
    path('agendamentos/excluir/<int:pk>/', views.excluir_agendamento, name='excluir_agendamento'),
    path('agendamentos/<int:pk>/fotos/', views.agendamento_fotos, name='agendamento_fotos'),
    path('agendamentos/<int:pk>/assinatura/', AdicionarAssinaturaView.as_view(), name='adicionar_assinatura'), 
    path('agendamentos/<int:pk>/checklist_carro/', checklist_carro, name='checklist_carro'),
    path('checklist/<str:tipo>/', views.checklist, name='criar_checklist'),
   
    
    # URLs de Relatórios
    path('relatorios/', views.relatorios, name='relatorios'),
    path('relatorios/carros/excel/', views.exportar_excel, {'relatorio_tipo': 'carros'}, name='carros_excel'),
    path('relatorios/agendamentos/excel/', views.exportar_excel, {'relatorio_tipo': 'agendamentos'}, name='agendamentos_excel'),
    path('relatorios/carros/word/', views.exportar_word, {'relatorio_tipo': 'carros'}, name='relatorio_carros_word'),
    path('relatorios/agendamentos/word/', views.exportar_word, {'relatorio_tipo': 'agendamentos'}, name='relatorio_agendamentos_word'),
    path('relatorios/carros/xml/', views.exportar_xml, {'relatorio_tipo': 'carros'}, name='relatorio_carros_xml'),
    path('relatorios/agendamentos/xml/', views.exportar_xml, {'relatorio_tipo': 'agendamentos'}, name='relatorio_agendamentos_xml'),
    path('agendamento/<int:agendamento_id>/relatorio_fotografico_word/', relatorio_fotografico_word, name='relatorio_fotografico_word'),
    path('checklist/<int:checklist_id>/relatorio_word/', views.relatorio_checklist_word, name='relatorio_checklist_word'),
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
   
]

