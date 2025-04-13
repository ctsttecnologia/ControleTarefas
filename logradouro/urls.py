from django.urls import path
from . import views

app_name = 'logradouro'

urlpatterns = [
    path('logradouro/', views.logradouro, name='logradouro'),
    path('logradouro/editar/<int:pk>/', views.editar_logradouro, name='editar_logradouro'),
    path('logradouro/excluir/<int:pk>/', views.excluir_logradouro, name='excluir_logradouro'),
]
