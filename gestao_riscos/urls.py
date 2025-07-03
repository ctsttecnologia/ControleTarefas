# epi/urls.py

from django.urls import path
from . import views

app_name = 'gestao_riscos'

urlpatterns = [
    path('', views.gestao_riscos, name='lista_riscos'),
    path('incidentes/registrar/', views.registrar_incidente, name='registrar_incidente'),

    # NOVA URL para o formulário de agendamento de inspeção
    path('inspecoes/agendar/', views.agendar_inspecao, name='agendar_inspecao'),
]


