# departamento_pessoal/urls.py
from django.urls import path

from .views import (
    # Painel
    PainelDPView,
    # Funcionários
    FuncionarioListView, FuncionarioDetailView, FuncionarioCreateView,
    FuncionarioUpdateView, FuncionarioDeleteView, FuncionarioAdmissaoView,
    # Departamentos
    DepartamentoListView, DepartamentoCreateView, DepartamentoUpdateView,
    # Cargos
    CargoListView, CargoCreateView, CargoUpdateView,
    # Documentos
    DocumentoListView, DocumentoCreateView, DocumentoUpdateView, DocumentoDeleteView,
    # Exportações
    ExportarFuncionariosExcelView, ExportarFuncionariosPDFView, ExportarFuncionariosWordView,
    # Upload / Importação (legado)
    UploadFuncionariosView, baixar_modelo_funcionarios, baixar_relatorio_erros,
    # Importação em Massa (novo serviço)
    download_modelo_funcionarios_view, importacao_massa_funcionarios_view,
)

app_name = 'departamento_pessoal'

urlpatterns = [
    # ─────────────────────────────────────────────────────
    # Dashboard
    # ─────────────────────────────────────────────────────
    path('painel/', PainelDPView.as_view(), name='painel_dp'),

    # ─────────────────────────────────────────────────────
    # CRUD — Funcionários
    # ─────────────────────────────────────────────────────
    path('funcionarios/', FuncionarioListView.as_view(), name='lista_funcionarios'),
    path('funcionarios/novo/', FuncionarioCreateView.as_view(), name='funcionario_create'),
    path('funcionarios/<int:pk>/', FuncionarioDetailView.as_view(), name='detalhe_funcionario'),
    path('funcionarios/<int:pk>/editar/', FuncionarioUpdateView.as_view(), name='editar_funcionario'),
    path('funcionarios/<int:pk>/excluir/', FuncionarioDeleteView.as_view(), name='funcionario_delete'),
    path('funcionarios/<int:pk>/admissao/', FuncionarioAdmissaoView.as_view(), name='adicionar_admissao'),

    # ─────────────────────────────────────────────────────
    # CRUD — Departamentos
    # ─────────────────────────────────────────────────────
    path('departamentos/', DepartamentoListView.as_view(), name='lista_departamento'),
    path('departamentos/novo/', DepartamentoCreateView.as_view(), name='departamento_form'),
    path('departamentos/<int:pk>/editar/', DepartamentoUpdateView.as_view(), name='departamento_update'),

    # ─────────────────────────────────────────────────────
    # CRUD — Cargos
    # ─────────────────────────────────────────────────────
    path('cargos/', CargoListView.as_view(), name='lista_cargo'),
    path('cargos/novo/', CargoCreateView.as_view(), name='cargo_form'),
    path('cargos/<int:pk>/editar/', CargoUpdateView.as_view(), name='edita_cargo'),

    # ─────────────────────────────────────────────────────
    # CRUD — Documentos
    # ─────────────────────────────────────────────────────
    path('documentos/', DocumentoListView.as_view(), name='lista_documentos'),
    path('documentos/novo/', DocumentoCreateView.as_view(), name='criar_documento'),
    path('documentos/novo/<int:funcionario_pk>/', DocumentoCreateView.as_view(), name='adicionar_documento'),
    path('documentos/<int:pk>/editar/', DocumentoUpdateView.as_view(), name='editar_documentos'),
    path('documentos/<int:pk>/excluir/', DocumentoDeleteView.as_view(), name='excluir_documento'),

    # ─────────────────────────────────────────────────────
    # Relatórios / Exportações
    # ─────────────────────────────────────────────────────
    path('funcionarios/exportar/excel/', ExportarFuncionariosExcelView.as_view(), name='exportar_excel'),
    path('funcionarios/exportar/pdf/', ExportarFuncionariosPDFView.as_view(), name='exportar_pdf'),
    path('funcionarios/exportar/word/', ExportarFuncionariosWordView.as_view(), name='exportar_word'),

    # ─────────────────────────────────────────────────────
    # Upload / Importação (legado)
    # ─────────────────────────────────────────────────────
    path('funcionarios/upload/', UploadFuncionariosView.as_view(), name='upload_funcionarios'),
    path('funcionarios/upload/modelo/', baixar_modelo_funcionarios, name='baixar_modelo_funcionarios'),
    path('funcionarios/upload/relatorio-erros/', baixar_relatorio_erros, name='baixar_relatorio_erros'),

    # ─────────────────────────────────────────────────────
    # Importação em Massa (novo serviço)
    # ─────────────────────────────────────────────────────
    path('importacao/', importacao_massa_funcionarios_view, name='importacao_massa_funcionarios'),
    path('importacao/modelo/', download_modelo_funcionarios_view, name='download_modelo_importacao_funcionarios'),
]


