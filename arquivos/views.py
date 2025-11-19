from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from .models import Arquivo
# AQUI ESTAVA O ERRO: Mudamos de DocumentoForm para ArquivoForm
from .forms import ArquivoForm 

class ArquivoListView(LoginRequiredMixin, ListView):
    model = Arquivo
    template_name = 'arquivos/lista.html'
    context_object_name = 'arquivos'

    def get_queryset(self):
        # Filtra pela filial e já traz os documentos anexados para otimizar
        return Arquivo.objects.filter(
            filial=self.request.user.filial_ativa
        ).prefetch_related('documentos_anexados')

class ArquivoCreateView(LoginRequiredMixin, CreateView):
    model = Arquivo
    form_class = ArquivoForm  # <--- Atualizado aqui também
    template_name = 'arquivos/form.html'
    success_url = reverse_lazy('arquivos:lista_documentos') # Verifique se o name no urls.py é 'lista_documentos' ou 'lista'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save(user=self.request.user)
        return redirect(self.success_url)

class ArquivoUpdateView(LoginRequiredMixin, UpdateView):
    model = Arquivo
    form_class = ArquivoForm  # <--- Atualizado aqui também
    template_name = 'arquivos/form.html'
    success_url = reverse_lazy('arquivos:lista_documentos')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save(user=self.request.user)
        return redirect(self.success_url)

class ArquivoDeleteView(LoginRequiredMixin, DeleteView):
    model = Arquivo
    template_name = 'arquivos/arquivo_confirm_delete.html' # Confirme se o template tem esse nome
    success_url = reverse_lazy('arquivos:lista_documentos')