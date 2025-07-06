# departamento_pessoal/views.py

from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from .models import Funcionario, Departamento, Cargo, Documento
from .forms import FuncionarioForm, DepartamentoForm, CargoForm, DocumentoForm

class StaffRequiredMixin(PermissionRequiredMixin):
    """
    Mixin que garante que o usuário tem permissão para acessar
    as views do departamento pessoal. Altere a permissão conforme necessário.
    """
    permission_required = 'auth.view_user' # Exemplo: apenas quem pode ver usuários
    raise_exception = True # Levanta um erro 403 se não tiver permissão

# --- VIEWS PARA FUNCIONÁRIOS ---

class FuncionarioListView(StaffRequiredMixin, ListView):
    model = Funcionario
    template_name = 'departamento_pessoal/funcionario_list.html'
    context_object_name = 'funcionarios'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cargo', 'departamento').order_by('nome_completo')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(nome_completo__icontains=query) |
                Q(matricula__icontains=query) |
                Q(cargo__nome__icontains=query)
            )
        return queryset

class FuncionarioDetailView(StaffRequiredMixin, DetailView):
    model = Funcionario
    template_name = 'departamento_pessoal/funcionario_detail.html'
    context_object_name = 'funcionario'

class FuncionarioCreateView(StaffRequiredMixin, CreateView):
    model = Funcionario
    form_class = FuncionarioForm
    template_name = 'departamento_pessoal/funcionario_form.html'

    def get_success_url(self):
        messages.success(self.request, "Funcionário cadastrado com sucesso!")
        return reverse_lazy('departamento_pessoal:funcionario_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = "Cadastrar Novo Funcionário"
        return context

class FuncionarioUpdateView(StaffRequiredMixin, UpdateView):
    model = Funcionario
    form_class = FuncionarioForm
    template_name = 'departamento_pessoal/funcionario_form.html'

    def get_success_url(self):
        messages.success(self.request, "Dados do funcionário atualizados com sucesso!")
        return reverse_lazy('departamento_pessoal:funcionario_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar: {self.object.nome_completo}"
        return context

class FuncionarioDeleteView(StaffRequiredMixin, DeleteView):
    model = Funcionario
    template_name = 'departamento_pessoal/confirm_delete.html'
    success_url = reverse_lazy('departamento_pessoal:funcionario_list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Funcionário '{self.object.nome_completo}' foi excluído.")
        return super().form_valid(form)


# --- VIEWS PARA DEPARTAMENTO E CARGO ---
# (Páginas para gerenciar os cadastros auxiliares)

class DepartamentoListView(StaffRequiredMixin, ListView):
    model = Departamento
    template_name = 'departamento_pessoal/departamento_list.html'
    context_object_name = 'departamentos'

class DepartamentoCreateView(StaffRequiredMixin, CreateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'departamento_pessoal/auxiliar_form.html'
    success_url = reverse_lazy('departamento_pessoal:departamento_list')
    extra_context = {'titulo_pagina': 'Novo Departamento'}

class DepartamentoUpdateView(StaffRequiredMixin, UpdateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'departamento_pessoal/auxiliar_form.html'
    success_url = reverse_lazy('departamento_pessoal:departamento_list')
    extra_context = {'titulo_pagina': 'Editar Departamento'}


class CargoListView(StaffRequiredMixin, ListView):
    model = Cargo
    template_name = 'departamento_pessoal/cargo_list.html'
    context_object_name = 'cargos'

class CargoCreateView(StaffRequiredMixin, CreateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'departamento_pessoal/auxiliar_form.html'
    success_url = reverse_lazy('departamento_pessoal:cargo_list')
    extra_context = {'titulo_pagina': 'Novo Cargo'}

class CargoUpdateView(StaffRequiredMixin, UpdateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'departamento_pessoal/auxiliar_form.html'
    success_url = reverse_lazy('departamento_pessoal:cargo_list')
    extra_context = {'titulo_pagina': 'Editar Cargo'}
