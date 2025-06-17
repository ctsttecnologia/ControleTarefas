from django.urls import path
from . import views
from .views import (
    EditarAdmissaoView, 
    NovaAdmissaoView, 
    CadastroAuxiliarView,
    CadastrarDepartamentoView, 
    CadastrarCboView, 
    CadastrarCargoView,
    FuncionarioDetailView,
    ListaAdmissoesView,
    DetalhesAdmissaoView,
    cadastrar_documentos, 
    editar_documentos,
    ListaDocumentosView,
    #DocumentoUpdateView,
    #DocumentoDeleteView,
    #DocumentoDetailView
    
)

app_name = 'departamento_pessoal'

urlpatterns = [
    # URLs principais
    path('', views.departamento_pessoal, name='departamento_pessoal'),
    
    # URLs de Funcionários
    path('funcionarios/', views.lista_funcionarios, name='lista_funcionarios'),
    path('funcionarios/cadastrar/', views.cadastrar_funcionario, name='cadastrar_funcionario'),
    path('funcionarios/<int:pk>/', FuncionarioDetailView.as_view(), name='detalhe_funcionario'),
    path('funcionarios/<int:pk>/editar/', views.editar_funcionario, name='editar_funcionario'),
    path('funcionarios/<int:pk>/excluir/', views.confirmar_exclusao, name='confirmar_exclusao'),
    
    # URLs de Documentos
    path('documentos/', ListaDocumentosView.as_view(), name='lista_documentos'),
    path('funcionarios/<int:funcionario_pk>/documentos/', cadastrar_documentos, name='cadastrar_documentos'),
    #path('funcionarios/<int:funcionario_pk>/documentos/editar/<int:pk>/', editar_documentos, name='editar_documentos'),
    path('funcionarios/<int:funcionario_pk>/documentos/editar/<int:pk>/', views.editar_documentos, name='editar_documentos'),

    # Paths complementares para CRUD de documentos
    #path('documentos/cadastrar/', DocumentoCreateView.as_view(), name='cadastrar_documento'),
    #path('documentos/<int:pk>/editar/', DocumentoUpdateView.as_view(), name='editar_documento'),
    #path('documentos/<int:pk>/excluir/', DocumentoDeleteView.as_view(), name='excluir_documento'),
    
    # URLs de Admissão
    path('admissoes/', ListaAdmissoesView.as_view(), name='lista_admissoes'),
    path('admissoes/<int:pk>/', DetalhesAdmissaoView.as_view(), name='detalhes_admissao'),
    path('funcionarios/<int:funcionario_pk>/admissao/nova/', NovaAdmissaoView.as_view(), name='nova_admissao'),
    #path('admissoes/<int:pk>/editar/', EditarAdmissaoView.as_view(), name='editar_admissao'),
    path('funcionarios/<int:funcionario_pk>/admissao/editar/<int:pk>', EditarAdmissaoView.as_view(), name='editar_admissao'),
    
    # URLs de Cadastro Auxiliar
    path('cadastro-auxiliar/', CadastroAuxiliarView.as_view(), name='cadastro_auxiliar'),
    path('cadastro-auxiliar/departamentos/', CadastrarDepartamentoView.as_view(), name='cadastrar_departamento'),
    path('cadastro-auxiliar/cbos/', CadastrarCboView.as_view(), name='cadastrar_cbo'),
    path('cadastro-auxiliar/cargos/', CadastrarCargoView.as_view(), name='cadastrar_cargo'),
    
    # URLs de API
    path('api/buscar-funcionario/', views.buscar_funcionario_por_matricula, name='buscar_funcionario'),
]