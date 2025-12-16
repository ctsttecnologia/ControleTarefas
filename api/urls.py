
# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView, LogoutView, MeView,
    TarefaViewSet,
    CarroViewSet, AgendamentoViewSet, ChecklistViewSet,
    FichaEPIViewSet, EntregaEPIViewSet,
    TermoViewSet,
)

app_name = 'api'

router = DefaultRouter()
router.register(r'tarefas', TarefaViewSet, basename='tarefa')
router.register(r'carros', CarroViewSet, basename='carro')
router.register(r'agendamentos', AgendamentoViewSet, basename='agendamento')
router.register(r'checklists', ChecklistViewSet, basename='checklist')
router.register(r'fichas-epi', FichaEPIViewSet, basename='fichaepi')
router.register(r'entregas-epi', EntregaEPIViewSet, basename='entregaepi')
router.register(r'termos', TermoViewSet, basename='termo')

urlpatterns = [
    # Autenticação
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', MeView.as_view(), name='me'),
    
    # Rotas do Router
    path('', include(router.urls)),
]


