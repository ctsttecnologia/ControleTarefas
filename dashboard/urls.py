# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',              views.DashboardGeralView.as_view(),        name='dashboard_geral'),
    path('treinamentos/', views.DashboardTreinamentosView.as_view(), name='dashboard_treinamentos'),
    path('tarefas/',      views.DashboardTarefasView.as_view(),      name='dashboard_tarefas'),
    path('epi/',          views.DashboardEpiView.as_view(),          name='dashboard_epi'),
    path('documentos/',   views.DashboardDocumentosView.as_view(),   name='dashboard_documentos'),
    path('pgr/',          views.DashboardPgrView.as_view(),          name='dashboard_pgr'),
]

