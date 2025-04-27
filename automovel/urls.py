from django.urls import path
from . import views
from .views import relatorio_fotos_pdf



app_name = 'automovel'

urlpatterns = [
    # Carros
    path('carros/', views.lista_carros, name='lista_carros'),
    path('carros/adicionar/', views.adicionar_carro, name='adicionar_carro'),
    path('carros/editar/<int:pk>/', views.editar_carro, name='editar_carro'),
    path('carros/excluir/<int:pk>/', views.excluir_carro, name='excluir_carro'),
    
    # Agendamentos
    path('agendamentos/', views.lista_agendamentos, name='lista_agendamentos'),
    path('agendamentos/adicionar/', views.adicionar_agendamento, name='adicionar_agendamento'),
    path('editar/<int:pk>/', views.editar_agendamento, name='editar_agendamento'),
    path('excluir/<int:pk>/', views.excluir_agendamento, name='excluir_agendamento'),
    path('assinar/<int:pk>/', views.assinar_agendamento, name='assinar_agendamento'),
    path('agendamento/<int:pk>/fotos/', views.agendamento_fotos, name='agendamento_fotos'),
    path('assinar/<int:pk>/', views.assinar_agendamento, name='assinar_agendamento'),

    # Relatórios
    path('relatorios/', views.relatorios, name='relatorios'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('agendamento/<int:pk>/relatorio-foto/', views.relatorio_fotos_pdf, name='relatorio_foto_pdf'),
    path('relatorios/carros/pdf/', views.exportar_pdf, {'relatorio_tipo': 'carros'}, name='carros_pdf'),
    path('relatorios/agendamentos/pdf/', views.exportar_pdf, {'relatorio_tipo': 'agendamentos'}, name='agendamentos_pdf'),
    path('relatorios/carros/excel/', views.exportar_excel, {'relatorio_tipo': 'carros'}, name='carros_excel'),
    path('relatorios/agendamentos/excel/', views.exportar_excel, {'relatorio_tipo': 'agendamentos'}, name='agendamentos_excel'),

    path('checklist/<str:tipo>/', views.checklist, name='checklist'),
    #path('checklists/', views.lista_checklists, name='lista_checklists'),
    #path('checklist/<int:pk>/', views.detalhes_checklist, name='detalhes_checklist'),
    path('checklist/<int:agendamento_id>/<str:tipo>/', views.checklist, name='criar_checklist'),
    path('agendamentos/<int:agendamento_id>/checklist/', views.formulario_checklist, name='formulariochecklist'),
]

