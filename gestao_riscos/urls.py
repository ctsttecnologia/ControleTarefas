# epi/urls.py


from django.urls import path
from . import views

app_name = 'gestao_riscos'

urlpatterns = [
    # Rota principal aponta para a view de Dashboard
    path('', views.GestaoRiscosDashboardView.as_view(), name='lista_riscos'),
    
    # Rota para registrar incidente aponta para a CreateView de Incidente
    path('incidentes/registrar/', views.RegistrarIncidenteView.as_view(), name='registrar_incidente'),

    # Rota para agendar inspeção aponta para a CreateView de Inspeção
    path('inspecoes/agendar/', views.AgendarInspecaoView.as_view(), name='agendar_inspecao'),
]


