# departamento_pessoal/urls.py
from django.urls import path
from .views import (
    DocumentoCreateView, DocumentoListView, DocumentoUpdateView, 
    ExportarFuncionariosPDFView, ExportarFuncionariosExcelView, ExportarFuncionariosWordView,
    FuncionarioAdmissaoView, FuncionarioListView, FuncionarioDetailView, 
    FuncionarioCreateView, FuncionarioUpdateView, FuncionarioDeleteView,
    DepartamentoListView, DepartamentoCreateView, DepartamentoUpdateView,
    CargoListView, CargoCreateView, CargoUpdateView, PainelDPView
)

app_name = 'departamento_pessoal'

urlpatterns = [
    # A rota principal da app agora será a lista de funcionários
    path('painel_dp', PainelDPView.as_view(), name='painel_dp'),
    
    
    # Rotas para o CRUD de Funcionários
    path('funcionarios', FuncionarioListView.as_view(), name='lista_funcionarios'),
    path('funcionarios/novo/', FuncionarioCreateView.as_view(), name='funcionario_create'),
    path('funcionarios/<int:pk>/', FuncionarioDetailView.as_view(), name='detalhe_funcionario'),
    path('funcionarios/<int:pk>/editar/', FuncionarioUpdateView.as_view(), name='editar_funcionario'),
    path('funcionarios/<int:pk>/excluir/', FuncionarioDeleteView.as_view(), name='funcionario_delete'),

    # NOVA URL PARA O PROCESSO DE ADMISSÃO
    path('funcionarios/<int:pk>/admissao/', FuncionarioAdmissaoView.as_view(), name='adicionar_admissao'),

    # Rotas para o CRUD de Departamentos
    path('departamentos/', DepartamentoListView.as_view(), name='lista_departamento'),
    path('departamentos/novo/', DepartamentoCreateView.as_view(), name='departamento_form'),
    path('departamentos/<int:pk>/editar/', DepartamentoUpdateView.as_view(), name='departamento_update'),
    
    # Rotas para o CRUD de Cargos
    path('cargos/', CargoListView.as_view(), name='lista_cargo'),
    path('cargos/novo/', CargoCreateView.as_view(), name='cargo_form'),
    path('cargos/<int:pk>/editar/', CargoUpdateView.as_view(), name='cargo_update'),

    # Rota para exibir a lista de todos os documentos.
    # O nome 'lista_documentos' permite referenciar esta URL em templates.
    path('documentos/', DocumentoListView.as_view(), name='lista_documentos'),
    # Rota para criar um novo documento sem um funcionário pré-definido.
    path('documentos/novo/', DocumentoCreateView.as_view(), name='documento_create'),
    # Rota para criar um novo documento, mas já associando a um funcionário específico
    # através de um parâmetro na URL (<int:funcionario_pk>).
    path('documentos/novo/<int:funcionario_pk>/', DocumentoCreateView.as_view(), name='adicionar_documento'),
    # Rota para editar um documento existente, identificado pelo seu ID (<int:pk>).
    path('documentos/<int:pk>/editar/', DocumentoUpdateView.as_view(), name='editar_documentos'),

    # Rotas para relatórios
    path('funcionarios/exportar/excel/', ExportarFuncionariosExcelView.as_view(), name='exportar_excel'),
    path('funcionarios/exportar/pdf/', ExportarFuncionariosPDFView.as_view(), name='exportar_pdf'),
    path('funcionarios/exportar/word/', ExportarFuncionariosWordView.as_view(), name='exportar_word'),
]

