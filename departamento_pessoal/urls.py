from django.urls import path
from . import views

app_name = 'departamento_pessoal'  # Adicionando namespace

urlpatterns = [
   
    path('departamento_pessoal/', views.departamento_pessoal, name='departamento_pessoal'),

    path('lista_funcionarios', views.lista_funcionarios, name='lista_funcionarios'),
    path('cadastrar/', views.cadastrar_funcionario, name='cadastrar_funcionario'),
    path('funcionario/novo/', views.cadastrar_funcionario, name='cadastrar_funcionario'),
    path('funcionario/<int:funcionario_id>/documentos/', views.cadastrar_documentos, name='cadastrar_documentos'),
    path('funcionario/editar/<int:pk>/', views.editar_funcionario, name='editar_funcionario'),
    #path('detalhes/<int:pk>/', views.detalhes_funcionario, name='detalhes_funcionario'),
    path('excluir/<int:pk>/', views.excluir_funcionario, name='excluir_funcionario'),
    path('funcionario/<int:pk>/', views.FuncionarioDetailView.as_view(), name='detalhes_funcionario'),

    path('admissao/', views.ListaAdmissoesView.as_view(), name='lista_admissao'),
    path('admissao/nova/<int:funcionario_pk>/', views.NovaAdmissaoView.as_view(), name='nova_admissao'),
    path('admissao/editar/<int:pk>/', views.EditarAdmissaoView.as_view(), name='editar_admissao'),
    
]

