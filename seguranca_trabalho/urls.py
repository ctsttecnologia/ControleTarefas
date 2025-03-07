from django.urls import path
from . import views

urlpatterns = [
    
    path('seguranca_trabalho/', views.seguranca_trabalho, name='seguranca_trabalho'),
    
]