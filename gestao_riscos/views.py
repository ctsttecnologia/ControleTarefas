# gestao_riscos/views.py


from time import timezone
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, DeleteView, UpdateView, DetailView, TemplateView, View
)
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q
import datetime
from automovel.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required

# --- Imports de Mixins ---
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
        #    de inspeções. 
        
        # O campo em 'Inspecao' que liga ao User agora é 'responsavel'
        inspecao_scoper = TecnicoScopeMixin()
        inspecao_scoper.request = self.request
        inspecao_scoper.tecnico_scope_lookup = 'responsavel' # Campo no modelo Inspecao
        
        qs_inspecoes_scoped = inspecao_scoper.scope_tecnico_queryset(qs_inspecoes_base)
            
        # Adiciona inspeções pendentes
        context['inspecoes_pendentes'] = qs_inspecoes_scoped.filter(
            status='PENDENTE'
        ).order_by('data_agendada')
        
        # NOVO: Adiciona inspeções propostas que o usuário pode ver
        context['inspecoes_propostas'] = qs_inspecoes_scoped.filter(
            status='PENDENTE_APROVACAO'
        ).order_by('data_agendada')
        
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
    success_url = reverse_lazy('gestao_riscos:calendario') # Mudar para o calendário
    success_message = "Inspeção agendada com sucesso!"
    permission_required = 'gestao_riscos.add_inspecao'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    # NOVO: Adicionado para pré-preencher a data vinda do calendário
    def get_initial(self):
        initial = super().get_initial()
        # Pega a data da URL (ex: ?data=2025-10-25)
        data_selecionada = self.request.GET.get('data')
        if data_selecionada:
            try:
                # Converte para o formato que o DateField espera
                initial['data_agendada'] = datetime.date.fromisoformat(data_selecionada)
            except ValueError:
                pass # Ignora data inválida
        
        # Define o responsável padrão como o usuário logado
        initial['responsavel'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Agendar Nova Inspeção'
        return context
    
# NOVAS VIEWS - CALENDÁRIO E APROVAÇÃO

class CalendarioView(LoginRequiredMixin, SSTPermissionMixin, TemplateView):
    """ Renderiza a página principal do calendário."""
    template_name = 'gestao_riscos/calendario.html'
    permission_required = 'gestao_riscos.view_inspecao'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Calendário de Inspeções'
        return context

# Esta é uma view de API, não uma página HTML
@login_required
def inspecao_events_api(request):
    """
    Fornece os eventos de inspeção em formato JSON para o FullCalendar.
    Aplica os mesmos filtros de escopo que o dashboard.
    """
    # 1. Filtra pela Filial do usuário
    qs_base = Inspecao.objects.for_request(request)
    
    # 2. Filtra pelo escopo do Técnico (se aplicável)
    scoper = TecnicoScopeMixin()
    scoper.request = request
    scoper.tecnico_scope_lookup = 'responsavel'
    qs_scoped = scoper.scope_tecnico_queryset(qs_base)
    
    # 3. Filtra por status visíveis no calendário
    qs_final = qs_scoped.filter(
        status__in=['PENDENTE', 'PENDENTE_APROVACAO', 'CONCLUIDA']
    ).select_related('equipamento', 'responsavel')

    eventos = []
    for inspecao in qs_final:
        # Define cor baseada no status
        if inspecao.status == 'CONCLUIDA':
            color = '#28a745' # Verde
        elif inspecao.status == 'PENDENTE_APROVACAO':
            color = '#ffc107' # Amarelo
        else: # PENDENTE
            color = '#007bff' # Azul
        
        # Título do evento
        titulo = f"{inspecao.equipamento.nome if inspecao.equipamento else 'Inspeção'}"
        if inspecao.responsavel:
            titulo += f" ({inspecao.responsavel.get_short_name()})"
            
        eventos.append({
            'id': inspecao.id,
            'title': titulo,
            'start': inspecao.data_agendada.isoformat(),
            'url': inspecao.get_absolute_url(), # Link para o detalhe
            'color': color,
            'allDay': True
        })

    return JsonResponse(eventos, safe=False)

class ListaInspecoesPropostasView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, ListView):
    """
    Exibe uma lista de inspeções que foram propostas automaticamente
    e aguardam confirmação do usuário.
    """
    model = Inspecao
    template_name = 'gestao_riscos/inspecoes_propostas_list.html'
    context_object_name = 'inspecoes_propostas'
    permission_required = 'gestao_riscos.change_inspecao' # Permissão para 'confirmar'
    
    # Configuração dos Mixins de Segurança
    tecnico_scope_lookup = 'responsavel' # Permite ver se for o responsável
    
    def get_queryset(self):
        # Chama o queryset filtrado pelos Mixins (Filial e Técnico)
        qs = super().get_queryset()
        
        # Se o usuário não for técnico, ele não verá nada (pois 'responsavel' está nulo)
        # Queremos que o técnico veja todas as propostas da sua filial
        if self.request.user.is_tecnico:
            # Reseta o filtro do TecnicoScopeMixin e aplica só o de filial
            qs = Inspecao.objects.for_request(self.request)
        
        # Filtra apenas as pendentes de aprovação
        return qs.filter(status='PENDENTE_APROVACAO').order_by('data_agendada')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Confirmar Inspeções Propostas'
        return context


class ConfirmarInspecaoView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, View):
    """
    View baseada em POST para confirmar uma inspeção proposta.
    """
    http_method_names = ['post']
    permission_required = 'gestao_riscos.change_inspecao'
    tecnico_scope_lookup = 'responsavel' # O Scoper não vai funcionar aqui (POST)
    
    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        # Garante que o usuário só pode confirmar inspeções da sua filial
        inspecao = get_object_or_404(
            Inspecao.objects.for_request(request), 
            pk=pk, 
            status='PENDENTE_APROVACAO'
        )
        
        # Confirma a inspeção
        inspecao.status = 'PENDENTE'
        inspecao.responsavel = request.user # Define o usuário logado como responsável
        inspecao.save()
        
        messages.success(request, f"Inspeção para '{inspecao.equipamento}' confirmada e atribuída a você.")
        
        # Redireciona de volta para a lista de propostas ou para o calendário
        if 'next' in request.POST:
            return HttpResponseRedirect(request.POST.get('next'))
        return redirect('gestao_riscos:lista_inspecoes_propostas')


class InspecaoDetailView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, DetailView):
    """
    View de detalhe para a inspeção (linkada do calendário).
    """
    model = Inspecao
    template_name = 'gestao_riscos/inspecao_detail.html' # Você precisará criar este template
    context_object_name = 'inspecao'
    permission_required = 'gestao_riscos.view_inspecao'
    tecnico_scope_lookup = 'responsavel'


class CompletarInspecaoView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, SuccessMessageMixin, UpdateView):
    """
    View para marcar uma inspeção como 'CONCLUÍDA'.
    """
    model = Inspecao
    template_name = 'gestao_riscos/inspecao_completar_form.html' # Você precisará criar este template
    form_class = InspecaoForm # Reutiliza o formulário principal
    success_url = reverse_lazy('gestao_riscos:calendario')
    success_message = "Inspeção marcada como Concluída!"
    permission_required = 'gestao_riscos.change_inspecao'
    tecnico_scope_lookup = 'responsavel'

    def get_form_kwargs(self):
        # Passa o request para o form (se o form precisar)
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        # Define o status e a data de realização
        form.instance.status = 'CONCLUIDA'
        if not form.instance.data_realizacao:
            form.instance.data_realizacao = timezone.now().date()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Concluir Inspeção: {self.object}"
        return context

# CRUD DE CARTÃO DE BLOQUEIO (TAG) - AGORA COM SEGURANÇA EM 3 NÍVEIS

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


