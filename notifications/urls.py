
# notifications/urls.py

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('<int:pk>/lida/', views.marcar_como_lida, name='marcar_como_lida',),
    path('marcar-todas/', views.marcar_todas_como_lidas, name='marcar_todas_como_lidas',),
    path('api/contagem/', views.api_contagem, name='api_contagem',),
]

