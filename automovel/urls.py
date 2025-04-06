from django.urls import path
from . import views

app_name = 'automovel'

urlpatterns = [
    # Carros
    path('carros/', views.lista_carros, name='lista_carros'),
    path('carros/adicionar/', views.adicionar_carro, name='adicionar_carro'),
    path('carros/editar/<str:renavan>/', views.editar_carro, name='editar_carro'),
    path('carros/excluir/<str:renavan>/', views.excluir_carro, name='excluir_carro'),
    
    # Agendamentos
    path('agendamentos/', views.lista_agendamentos, name='lista_agendamentos'),
    path('agendamentos/adicionar/', views.adicionar_agendamento, name='adicionar_agendamento'),
    path('agendamentos/editar/<int:pk>/', views.editar_agendamento, name='editar_agendamento'),
    path('agendamentos/excluir/<int:pk>/', views.excluir_agendamento, name='excluir_agendamento'),
    path('agendamentos/assinar/<int:pk>/', views.assinar_agendamento, name='assinar_agendamento'),
]