# gestao_riscos/views.py
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DeleteView, UpdateView, DetailView # Usaremos ListView para o dashboard
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from automovel.views import SuccessMessageMixin
from core.mixins import FilialScopedQuerysetMixin, FilialCreateMixin
from .forms import IncidenteForm, InspecaoForm, CartaoTagForm
from .models import Incidente, Inspecao, CartaoTag



class GestaoRiscosDashboardView(LoginRequiredMixin, FilialScopedQuerysetMixin, ListView):
    """
    Dashboard refatorado para usar ListView e o mixin de filtro de filial.
    Exibe uma lista de incidentes.
    """
    model = Incidente # Define o modelo principal para o mixin funcionar
    template_name = 'gestao_riscos/lista_riscos.html'
    context_object_name = 'incidentes' # O queryset principal será de incidentes

    def get_queryset(self):
        # O mixin já filtra pela filial, aqui apenas ordenamos e limitamos
        return super().get_queryset().order_by('-data_ocorrencia')[:10]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adiciona a lista de inspeções pendentes como um dado secundário
        # Usamos o mixin para filtrar Inspecao também, através do seu get_queryset()
        qs_inspecoes = Inspecao.objects.all()
        # Para usar a lógica do mixin em um segundo modelo, aplicamos manualmente
        filial_id = self.request.session.get('active_filial_id')
        if filial_id:
            qs_inspecoes = qs_inspecoes.filter(filial_id=filial_id)
        else: # Segurança: se não houver filial, não mostra nada
            qs_inspecoes = qs_inspecoes.none()
            
        context['inspecoes'] = qs_inspecoes.filter(status='PENDENTE').order_by('data_agendada')
        context['titulo_pagina'] = 'Dashboard de Gestão de Riscos'
        return context

class RegistrarIncidenteView(LoginRequiredMixin, FilialCreateMixin, SuccessMessageMixin, CreateView):
    """
    View de registro de incidente refatorada para usar FilialCreateMixin.
    """
    model = Incidente
    form_class = IncidenteForm
    template_name = 'gestao_riscos/registrar_incidente.html'
    success_url = reverse_lazy('gestao_riscos:lista_riscos')
    success_message = "Incidente registrado com sucesso!"

    def form_valid(self, form):
        # Associa o usuário logado (o mixin já cuida da filial)
        form.instance.registrado_por = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Registrar Novo Incidente'
        return context

class AgendarInspecaoView(LoginRequiredMixin, FilialCreateMixin, SuccessMessageMixin, CreateView):
    """
    View de agendamento de inspeção refatorada para usar FilialCreateMixin.
    """
    model = Inspecao
    form_class = InspecaoForm
    template_name = 'gestao_riscos/formulario_inspecao.html'
    success_url = reverse_lazy('gestao_riscos:lista_riscos')
    success_message = "Inspeção agendada com sucesso!"

    def get_form_kwargs(self):
        """Passa o objeto 'request' inteiro para o formulário."""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request # O form usará o request para pegar a filial da sessão
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Agendar Nova Inspeção'
        return context
    
# ========================================================================
# CRUD DE CARTÃO DE BLOQUEIO (TAG)
# ========================================================================

class CartaoTagListView(LoginRequiredMixin, FilialScopedQuerysetMixin, ListView):
    model = CartaoTag
    template_name = 'gestao_riscos/cartao_tag_list.html'
    context_object_name = 'cartoes'
    paginate_by = 10

class CartaoTagDetailView(LoginRequiredMixin, FilialScopedQuerysetMixin, DetailView):
    model = CartaoTag
    template_name = 'gestao_riscos/cartao_tag_detail.html'
    context_object_name = 'cartao'

class CartaoTagCreateView(LoginRequiredMixin, FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = CartaoTag
    form_class = CartaoTagForm
    template_name = 'gestao_riscos/cartao_tag_form.html'
    success_url = reverse_lazy('gestao_riscos:cartao_tag_list')
    success_message = "Cartão de Bloqueio criado com sucesso!"

    def get_form_kwargs(self):
        """Passa o request para o formulário para filtrar o campo 'funcionário'."""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

class CartaoTagUpdateView(LoginRequiredMixin, FilialScopedQuerysetMixin, SuccessMessageMixin, UpdateView):
    model = CartaoTag
    form_class = CartaoTagForm
    template_name = 'gestao_riscos/cartao_tag_form.html'
    success_url = reverse_lazy('gestao_riscos:cartao_tag_list')
    success_message = "Cartão de Bloqueio atualizado com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

class CartaoTagDeleteView(LoginRequiredMixin, FilialScopedQuerysetMixin, SuccessMessageMixin, DeleteView):
    model = CartaoTag
    template_name = 'gestao_riscos/cartao_tag_confirm_delete.html'
    success_url = reverse_lazy('gestao_riscos:cartao_tag_list')
    success_message = "Cartão de Bloqueio deletado com sucesso!"
