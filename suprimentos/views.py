# suprimentos/views.py
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from core.mixins import ViewFilialScopedMixin, FilialCreateMixin, SSTPermissionMixin # Reutilize seus mixins
from .models import Parceiro
from .forms import ParceiroForm

class ParceiroListView(ViewFilialScopedMixin, SSTPermissionMixin, ListView):
    model = Parceiro
    template_name = 'suprimentos/parceiro_list.html'
    context_object_name = 'parceiros'
    paginate_by = 15
    permission_required = 'suprimentos.view_parceiro' # Adapte as permissões conforme necessário

    def get_queryset(self):
        qs = super().get_queryset().order_by('nome_fantasia')
        query = self.request.GET.get('q')
        tipo = self.request.GET.get('tipo')

        if query:
            qs = qs.filter(
                Q(nome_fantasia__icontains=query) |
                Q(razao_social__icontains=query) |
                Q(cnpj__icontains=query)
            )
        
        if tipo == 'fabricante':
            qs = qs.filter(eh_fabricante=True)
        elif tipo == 'fornecedor':
            qs = qs.filter(eh_fornecedor=True)

        return qs

class ParceiroDetailView(ViewFilialScopedMixin, SSTPermissionMixin, DetailView):
    model = Parceiro
    template_name = 'suprimentos/parceiro_detail.html'
    context_object_name = 'parceiro'
    permission_required = 'suprimentos.view_parceiro'

class ParceiroCreateView(FilialCreateMixin, SSTPermissionMixin, CreateView):
    model = Parceiro
    form_class = ParceiroForm
    template_name = 'suprimentos/parceiro_form.html'
    success_url = reverse_lazy('suprimentos:parceiro_list')
    permission_required = 'suprimentos.add_parceiro'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Cadastrar Novo Parceiro'
        return context

class ParceiroUpdateView(ViewFilialScopedMixin, SSTPermissionMixin, UpdateView):
    model = Parceiro
    form_class = ParceiroForm
    template_name = 'suprimentos/parceiro_form.html'
    success_url = reverse_lazy('suprimentos:parceiro_list')
    permission_required = 'suprimentos.change_parceiro'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Editar Parceiro'
        return context

class ParceiroDeleteView(ViewFilialScopedMixin, SSTPermissionMixin, DeleteView):
    model = Parceiro
    template_name = 'suprimentos/parceiro_confirm_delete.html'
    success_url = reverse_lazy('suprimentos:parceiro_list')
    context_object_name = 'object'
    permission_required = 'suprimentos.delete_parceiro'
