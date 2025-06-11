from django.urls import path
from . import views
from .views import EditarAdmissaoView, NovaAdmissaoView, CadastroAuxiliarView, CadastrarDepartamentoView, CadastrarCboView, CadastrarCargoView
from .views import FuncionarioDetailView, detalhe_funcionario

app_name = 'departamento_pessoal'

urlpatterns = [
    path('', views.departamento_pessoal, name='departamento_pessoal'),
    path('funcionarios/', views.lista_funcionarios, name='lista_funcionarios'),
    path('funcionarios/cadastrar/', views.cadastrar_funcionario, name='cadastrar_funcionario'),
    path('funcionarios/<int:pk>/', FuncionarioDetailView.as_view(), name='detalhe_funcionario'),
    path('funcionarios/<int:pk>/editar/', views.editar_funcionario, name='editar_funcionario'),
    path('buscar-funcionario/', views.buscar_funcionario_por_matricula, name='buscar_funcionario'),
    path('funcionario/<int:pk>/excluir/', views.confirmar_exclusao, name='confirmar_exclusao'),
    path('funcionarios/<int:funcionario_pk>/documentos/editar/', views.cadastrar_documentos, name='editar_documentos'),
    path('funcionarios/<int:funcionario_pk>/documentos/', views.cadastrar_documentos, name='cadastrar_documentos'),

    # URLs de Admissão
    path('admissoes/', views.ListaAdmissoesView.as_view(), name='lista_admissoes'),
    path('admissoes/<int:pk>/', views.DetalhesAdmissaoView.as_view(), name='detalhes_admissao'),
    #path('funcionarios/<int:funcionario_pk>/nova-admissao/', NovaAdmissaoView.as_view(), name='nova_admissao'),
    path('funcionario/<int:funcionario_pk>/admissao/nova/', views.NovaAdmissaoView.as_view(), name='nova_admissao'),
    path('admissoes/<int:pk>/editar/', EditarAdmissaoView.as_view(), name='editar_admissao'),

    # Cadastro Auxiliar
    path('cadastro-auxiliar/', CadastroAuxiliarView.as_view(), name='cadastro_auxiliar'),
    path('cadastro-auxiliar/departamento/', CadastrarDepartamentoView.as_view(), name='cadastrar_departamento'),
    path('cadastro-auxiliar/cbo/', CadastrarCboView.as_view(), name='cadastrar_cbo'),
    path('cadastro-auxiliar/cargo/', CadastrarCargoView.as_view(), name='cadastrar_cargo'),

    # API
    path('api/buscar-funcionario/', views.buscar_funcionario_por_matricula, name='buscar_funcionario'),
]

    