# departamento_pessoal/urls.py
from django.urls import path
from .views import (
    FuncionarioListView, FuncionarioDetailView, FuncionarioCreateView, 
    FuncionarioUpdateView, FuncionarioDeleteView,
    DepartamentoListView, DepartamentoCreateView, DepartamentoUpdateView,
    CargoListView, CargoCreateView, CargoUpdateView,
)

app_name = 'departamento_pessoal'

urlpatterns = [
    # A rota principal da app agora será a lista de funcionários
    path('', FuncionarioListView.as_view(), name='funcionario_list'),
    
    # Rotas para o CRUD de Funcionários
    path('funcionarios/novo/', FuncionarioCreateView.as_view(), name='funcionario_create'),
    path('funcionarios/<int:pk>/', FuncionarioDetailView.as_view(), name='funcionario_detail'),
    path('funcionarios/<int:pk>/editar/', FuncionarioUpdateView.as_view(), name='funcionario_update'),
    path('funcionarios/<int:pk>/excluir/', FuncionarioDeleteView.as_view(), name='funcionario_delete'),

    # Rotas para o CRUD de Departamentos
    path('departamentos/', DepartamentoListView.as_view(), name='departamento_list'),
    path('departamentos/novo/', DepartamentoCreateView.as_view(), name='departamento_create'),
    path('departamentos/<int:pk>/editar/', DepartamentoUpdateView.as_view(), name='departamento_update'),
    
    # Rotas para o CRUD de Cargos
    path('cargos/', CargoListView.as_view(), name='cargo_list'),
    path('cargos/novo/', CargoCreateView.as_view(), name='cargo_create'),
    path('cargos/<int:pk>/editar/', CargoUpdateView.as_view(), name='cargo_update'),
]
