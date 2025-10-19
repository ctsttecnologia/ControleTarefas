# gestao_riscos/views.py
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DeleteView, UpdateView, DetailView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from automovel.views import SuccessMessageMixin

# --- Imports de Mixins ---
# Adicionado SSTPermissionMixin e TecnicoScopeMixin
from core.mixins import (
    SSTPermissionMixin, 
    ViewFilialScopedMixin, 
    FilialCreateMixin,
    TecnicoScopeMixin
)
from .forms import IncidenteForm, InspecaoForm, CartaoTagForm
from .models import Incidente, Inspecao, CartaoTag


class GestaoRiscosDashboardView(
    LoginRequiredMixin, 
    SSTPermissionMixin,      # Nível 1: Permissão da Página
    TecnicoScopeMixin,       # Nível 3: Escopo de Dados (Técnico)
    ViewFilialScopedMixin,   # Nível 2: Escopo de Filial
    ListView
):
    """
    Dashboard que exibe dados de Gestão de Riscos, aplicando a 
    arquitetura de segurança em 3 níveis.
    """
    model = Incidente  # Modelo principal da view
    template_name = 'gestao_riscos/lista_riscos.html'
    context_object_name = 'incidentes'

    # --- Configuração dos Mixins de Segurança ---
    permission_required = 'gestao_riscos.view_incidente' # Permissão para ver a página
    tecnico_scope_lookup = 'registrado_por' # Campo no modelo Incidente que liga ao User

    def get_queryset(self):
        """
        O queryset principal (incidentes) é filtrado automaticamente
        pelos mixins TecnicoScopeMixin e ViewFilialScopedMixin.
        """
        return super().get_queryset().order_by('-data_ocorrencia')[:10]

    def get_context_data(self, **kwargs):
        """
        Adiciona querysets secundários (inspeções) ao contexto, aplicando
        manualmente a mesma lógica de escopo para consistência.
        """
        context = super().get_context_data(**kwargs)
        
        # 1. Busca a base de inspeções já filtrada pela filial usando o manager
        qs_inspecoes_base = Inspecao.objects.for_request(self.request)

        # 2. Reutiliza a lógica do TecnicoScopeMixin para filtrar o queryset secundário
        #    de inspeções. Fazemos isso de forma segura, sem alterar o estado da view.
        #    Criamos uma instância temporária do mixin para aplicar o filtro.
        
        # Supondo que o campo em 'Inspecao' que liga ao User seja 'responsavel'
        inspecao_scoper = TecnicoScopeMixin()
        inspecao_scoper.request = self.request
        inspecao_scoper.tecnico_scope_lookup = 'responsavel' # Campo no modelo Inspecao
        
        qs_inspecoes_scoped = inspecao_scoper.scope_tecnico_queryset(qs_inspecoes_base)
            
        context['inspecoes'] = qs_inspecoes_scoped.filter(status='PENDENTE').order_by('data_agendada')
        context['titulo_pagina'] = 'Dashboard de Gestão de Riscos'
        return context


class RegistrarIncidenteView(LoginRequiredMixin, SSTPermissionMixin, FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = Incidente
    form_class = IncidenteForm
    template_name = 'gestao_riscos/registrar_incidente.html'
    success_url = reverse_lazy('gestao_riscos:lista_riscos')
    success_message = "Incidente registrado com sucesso!"
    permission_required = 'gestao_riscos.add_incidente'

    def form_valid(self, form):
        form.instance.registrado_por = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Registrar Novo Incidente'
        return context


class AgendarInspecaoView(LoginRequiredMixin, SSTPermissionMixin, FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = Inspecao
    form_class = InspecaoForm
    template_name = 'gestao_riscos/formulario_inspecao.html'
    success_url = reverse_lazy('gestao_riscos:lista_riscos')
    success_message = "Inspeção agendada com sucesso!"
    permission_required = 'gestao_riscos.add_inspecao'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Agendar Nova Inspeção'
        return context
    

# ========================================================================
# CRUD DE CARTÃO DE BLOQUEIO (TAG) - AGORA COM SEGURANÇA EM 3 NÍVEIS
# ========================================================================

class CartaoTagListView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, ListView):
    model = CartaoTag
    template_name = 'gestao_riscos/cartao_tag_list.html'
    context_object_name = 'cartoes'
    paginate_by = 10
    permission_required = 'gestao_riscos.view_cartaotag'
    # Supondo que o campo em CartaoTag que liga ao User seja 'responsavel'
    tecnico_scope_lookup = 'responsavel'


class CartaoTagDetailView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, DetailView):
    model = CartaoTag
    template_name = 'gestao_riscos/cartao_tag_detail.html'
    context_object_name = 'cartao'
    permission_required = 'gestao_riscos.view_cartaotag'
    tecnico_scope_lookup = 'responsavel'


class CartaoTagCreateView(LoginRequiredMixin, SSTPermissionMixin, FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = CartaoTag
    form_class = CartaoTagForm
    template_name = 'gestao_riscos/cartao_tag_form.html'
    success_url = reverse_lazy('gestao_riscos:cartao_tag_list')
    success_message = "Cartão de Bloqueio criado com sucesso!"
    permission_required = 'gestao_riscos.add_cartaotag'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class CartaoTagUpdateView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, SuccessMessageMixin, UpdateView):
    model = CartaoTag
    form_class = CartaoTagForm
    template_name = 'gestao_riscos/cartao_tag_form.html'
    success_url = reverse_lazy('gestao_riscos:cartao_tag_list')
    success_message = "Cartão de Bloqueio atualizado com sucesso!"
    permission_required = 'gestao_riscos.change_cartaotag'
    tecnico_scope_lookup = 'responsavel'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class CartaoTagDeleteView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, SuccessMessageMixin, DeleteView):
    model = CartaoTag
    template_name = 'gestao_riscos/cartao_tag_confirm_delete.html'
    success_url = reverse_lazy('gestao_riscos:cartao_tag_list')
    success_message = "Cartão de Bloqueio deletado com sucesso!"
    permission_required = 'gestao_riscos.delete_cartaotag'
    tecnico_scope_lookup = 'responsavel'


