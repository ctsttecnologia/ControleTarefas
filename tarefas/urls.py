from django.urls import path
from . import views

urlpatterns = [
    
    path('tarefas/', views.tarefas, name='tarefas'),
    
]