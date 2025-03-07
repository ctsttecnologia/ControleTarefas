from django.urls import path
from . import views

urlpatterns = [
   
    path('departamento_pessoal/', views.departamento_pessoal, name='departamento_pessoal'),
 
]