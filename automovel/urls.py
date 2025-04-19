from django.urls import path
from . import views



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

    # Relatórios
    path('relatorios/', views.relatorios, name='relatorios'),
    path('exportar/pdf/<str:tipo>/', views.exportar_pdf, name='exportar_pdf'),
    path('exportar/excel/<str:tipo>/', views.exportar_excel, name='exportar_excel'),
    path('dashboard/', views.dashboard, name='dashboard'),
]

