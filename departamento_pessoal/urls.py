from django.urls import path
from . import views



urlpatterns = [
   
    path('departamento_pessoal/', views.departamento_pessoal, name='departamento_pessoal'),
    path('lista_funcionarios', views.lista_funcionarios, name='lista_funcionarios'),
    path('cadastrar/', views.cadastrar_funcionario, name='cadastrar_funcionario'),
    path('detalhes/<int:id>/', views.detalhes_funcionario, name='detalhes_funcionario'),
    path('excluir/<int:id>/', views.excluir_funcionario, name='excluir_funcionario'),
    path('admissao/', views.admissao, name='admissao'),
    
]