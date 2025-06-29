# documents_app/urls.py

from django.urls import path
from .views import (
    CadastrarCargoView,
    CadastrarCboView,
    CadastrarDepartamentoView,
    CadastroAuxiliarView,
    DetalhesAdmissaoView,
    buscar_funcionario_por_matricula,
    check_email_exists,
    departamento_pessoal,
    lista_funcionarios,
    cadastrar_funcionario,
    FuncionarioDetailView,
    editar_funcionario,
    confirmar_exclusao_funcionario,
    cadastrar_documentos,
    editar_documentos,
    NovaAdmissaoView,
    EditarAdmissaoView,
    ListaAdmissoesView,

)

app_name = 'departamento_pessoal'

urlpatterns = [
    # --- Views Principais (baseadas em função) ---
    path('', departamento_pessoal, name='departamento_pessoal'),
    
    # --- URLs de Funcionários ---
    path('funcionarios/', lista_funcionarios, name='lista_funcionarios'),
    path('funcionarios/novo/', cadastrar_funcionario, name='cadastrar_funcionario'),
    path('funcionarios/<int:pk>/', FuncionarioDetailView.as_view(), name='detalhe_funcionario'), # É uma classe, usa .as_view()
    path('funcionarios/<int:pk>/editar/', editar_funcionario, name='editar_funcionario'),
    path('funcionarios/<int:pk>/excluir/', confirmar_exclusao_funcionario, name='confirmar_exclusao_funcionario'),
    
    # --- URLs de Documentos (baseadas em função) ---
    path('funcionarios/<int:funcionario_pk>/documentos/novo/', cadastrar_documentos, name='cadastrar_documentos'),
    path('funcionarios/<int:funcionario_pk>/documentos/<int:pk>/editar/', editar_documentos, name='editar_documentos'),
    
    # --- URLs de Admissão (aqui usamos classes) ---
    # CORREÇÃO: Aplicando .as_view() na sua nova URL
    path('admissoes/', ListaAdmissoesView.as_view(), name='lista_admissoes'),
    path('admissoes/<int:pk>/', DetalhesAdmissaoView.as_view(), name='detalhes_admissao'),
    path('funcionarios/<int:funcionario_pk>/admissao/nova/', NovaAdmissaoView.as_view(), name='nova_admissao'),
    path('admissoes/<int:pk>/editar/', EditarAdmissaoView.as_view(), name='editar_admissao'), # CORREÇÃO: Mantive uma URL mais simples, ajuste se necessário

    # --- URLs de Cadastro Auxiliar (classes) ---
    path('cadastro-auxiliar/', CadastroAuxiliarView.as_view(), name='cadastro_auxiliar'),
    path('cadastro-auxiliar/departamentos/', CadastrarDepartamentoView.as_view(), name='cadastrar_departamento'),
    path('cadastro-auxiliar/cbos/', CadastrarCboView.as_view(), name='cadastrar_cbo'),
    path('cadastro-auxiliar/cargos/', CadastrarCargoView.as_view(), name='cadastrar_cargo'),
    
    # --- URLs de API / AJAX (baseadas em função) ---
    path('api/buscar-funcionario/', buscar_funcionario_por_matricula, name='buscar_funcionario'),
    path('api/check-email/', check_email_exists, name='check_email'), # Adicionando um nome para a URL de checagem de email
]
