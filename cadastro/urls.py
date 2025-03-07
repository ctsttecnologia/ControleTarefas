from django.urls import path
from . import views



urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    
    #path('formulario/', views.formulario, name='formulario'),
]