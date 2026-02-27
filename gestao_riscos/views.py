
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
from seguranca_trabalho.models import EntregaEPI
from .forms import IncidenteForm, InspecaoForm, CartaoTagForm
from .models import CartaoTag, Incidente, Inspecao, TipoRisco, CATEGORIA_RISCO_CHOICES
from django.db.models import Q, Count
from .forms import TipoRiscoForm


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

# ===========================================
# TIPO DE RISCO — CRUD
# ===========================================

class TipoRiscoListView(LoginRequiredMixin, ListView, SSTPermissionMixin, ViewFilialScopedMixin):
    """Lista de Tipos de Riscos"""
    model = TipoRisco
    template_name = 'gestao_riscos/tipo_risco_list.html'
    context_object_name = 'tipos_risco'
    paginate_by = 20

    def get_queryset(self):
        qs = TipoRisco.objects.all()

        # Filtro por categoria
        categoria = self.request.GET.get('categoria')
        if categoria:
            qs = qs.filter(categoria=categoria)

        # Filtro apenas ativos
        ativo = self.request.GET.get('ativo')
        if ativo == 'true':
            qs = qs.filter(ativo=True)
        elif ativo == 'false':
            qs = qs.filter(ativo=False)

        # Busca por nome ou NR
        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(nome__icontains=search) |
                Q(nr_referencia__icontains=search) |
                Q(descricao__icontains=search)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        todos = TipoRisco.objects.all()
        context['total_tipos'] = todos.count()
        context['total_ativos'] = todos.filter(ativo=True).count()

        # Contagem por categoria com cor
        contagem = dict(
            todos.values('categoria').annotate(total=Count('id')).values_list('categoria', 'total')
        )

        categorias_info = []
        for cat_key, cat_label in CATEGORIA_RISCO_CHOICES:
            categorias_info.append({
                'key': cat_key,
                'label': cat_label,
                'total': contagem.get(cat_key, 0),
                'cor': TipoRisco.CORES_CATEGORIA.get(cat_key, '#808080'),
                'texto_escuro': cat_key == 'ergonomico',
            })

        context['categorias_info'] = categorias_info
        context['categorias'] = CATEGORIA_RISCO_CHOICES

        return context


class TipoRiscoCreateView(LoginRequiredMixin, CreateView, SSTPermissionMixin, ViewFilialScopedMixin, SuccessMessageMixin):
    """Cadastrar novo Tipo de Risco"""
    model = TipoRisco
    form_class = TipoRiscoForm
    template_name = 'gestao_riscos/tipo_risco_form.html'
    success_url = reverse_lazy('gestao_riscos:tipo_risco_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial'] = self.request.user.filial_ativa
        return kwargs

    def form_valid(self, form):
        form.instance.filial = self.request.user.filial_ativa
        messages.success(self.request, f'Tipo de Risco "{form.instance.nome}" cadastrado com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo Tipo de Risco'
        context['btn_texto'] = 'Cadastrar'
        context['cores_categorias'] = TipoRisco.CORES_CATEGORIA
        return context


class TipoRiscoUpdateView(LoginRequiredMixin, UpdateView, SSTPermissionMixin, ViewFilialScopedMixin, SuccessMessageMixin):
    """Editar Tipo de Risco"""
    model = TipoRisco
    form_class = TipoRiscoForm
    template_name = 'gestao_riscos/tipo_risco_form.html'
    success_url = reverse_lazy('gestao_riscos:tipo_risco_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial'] = self.request.user.filial_ativa
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Tipo de Risco "{form.instance.nome}" atualizado com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Tipo de Risco'
        context['btn_texto'] = 'Salvar Alterações'
        context['cores_categorias'] = TipoRisco.CORES_CATEGORIA
        return context


class TipoRiscoDeleteView(LoginRequiredMixin, DeleteView, SSTPermissionMixin, ViewFilialScopedMixin, SuccessMessageMixin):
    """Excluir Tipo de Risco"""
    model = TipoRisco
    template_name = 'gestao_riscos/tipo_risco_confirm_delete.html'
    success_url = reverse_lazy('gestao_riscos:tipo_risco_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f'Tipo de Risco "{obj.nome}" excluído com sucesso!')
        return super().delete(request, *args, **kwargs)


class TipoRiscoToggleAtivoView(LoginRequiredMixin, View, SSTPermissionMixin, ViewFilialScopedMixin):
    """Toggle ativo/inativo via AJAX"""

    def post(self, request, pk):
        try:
            tipo = TipoRisco.objects.get(pk=pk)
            tipo.ativo = not tipo.ativo
            tipo.save(update_fields=['ativo'])

            return JsonResponse({
                'success': True,
                'ativo': tipo.ativo,
                'message': f'"{tipo.nome}" {"ativado" if tipo.ativo else "inativado"} com sucesso!'
            })
        except TipoRisco.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Tipo de Risco não encontrado.'
            }, status=404)


class TipoRiscoPopularView(LoginRequiredMixin, View, SSTPermissionMixin, ViewFilialScopedMixin):
    """Popular tipos de risco padrão para a filial (dados iniciais)"""

    def post(self, request):
        filial = request.user.filial_ativa

        RISCOS_PADRAO = {
            'fisico': {
                'cor': '#00a651',
                'agentes': [
                    ('Ruído', 'NR-15'),
                    ('Vibrações', 'NR-15'),
                    ('Radiação Ionizante', 'NR-15'),
                    ('Radiação Não Ionizante', 'NR-15'),
                    ('Frio', 'NR-15'),
                    ('Calor', 'NR-15'),
                    ('Pressões Anormais', 'NR-15'),
                    ('Umidade', 'NR-15'),
                    ('Temperaturas Extremas', 'NR-15'),
                ],
            },
            'quimico': {
                'cor': '#ed1c24',
                'agentes': [
                    ('Poeiras', 'NR-15'),
                    ('Fumos Metálicos', 'NR-15'),
                    ('Névoas', 'NR-15'),
                    ('Neblinas', 'NR-15'),
                    ('Gases', 'NR-15'),
                    ('Vapores', 'NR-15'),
                    ('Substâncias, Compostos Químicos em Geral', 'NR-15'),
                ],
            },
            'biologico': {
                'cor': '#8B4513',
                'agentes': [
                    ('Vírus', 'NR-15'),
                    ('Bactérias', 'NR-15'),
                    ('Protozoários', 'NR-15'),
                    ('Fungos', 'NR-15'),
                    ('Parasitas', 'NR-15'),
                    ('Bacilos', 'NR-15'),
                    ('Insetos, Cobras, Aranhas, etc.', 'NR-15'),
                ],
            },
            'ergonomico': {
                'cor': '#f7ec13',
                'agentes': [
                    ('Esforço Físico Intenso', 'NR-17'),
                    ('Levantamento e Transporte Manual de Peso', 'NR-17'),
                    ('Exigência de Postura Inadequada', 'NR-17'),
                    ('Controle Rígido de Produtividade', 'NR-17'),
                    ('Imposição de Ritmos Excessivos', 'NR-17'),
                    ('Trabalho em Turno e Noturno', 'NR-17'),
                    ('Jornada de Trabalho Prolongada', 'NR-17'),
                    ('Monotonia e Repetitividade', 'NR-17'),
                    ('Outras Situações Causadoras de Stress Físico e/ou Psíquico', 'NR-17'),
                ],
            },
            'acidente': {
                'cor': '#0068b7',
                'agentes': [
                    ('Arranjo Físico Inadequado', 'NR-12'),
                    ('Máquinas e Equipamentos sem Proteção', 'NR-12'),
                    ('Ferramentas Inadequadas ou Defeituosas', 'NR-12'),
                    ('Eletricidade', 'NR-10'),
                    ('Probabilidade de Incêndio ou Explosão', 'NR-23'),
                    ('Armazenamento Inadequado', 'NR-11'),
                    ('Animais Peçonhentos', ''),
                    ('Iluminação Inadequada', 'NR-17'),
                    ('Outras Situações de Risco que Poderão Contribuir para Ocorrência de Acidentes', ''),
                ],
            },
        }

        criados = 0
        existentes = 0

        for categoria, info in RISCOS_PADRAO.items():
            for agente_nome, nr_ref in info['agentes']:
                obj, created = TipoRisco.objects.get_or_create(
                    categoria=categoria,
                    nome=agente_nome,
                    filial=filial,
                    defaults={
                        'codigo_cor': info['cor'],
                        'nr_referencia': nr_ref,
                        'ativo': True,
                    }
                )
                if created:
                    criados += 1
                else:
                    existentes += 1

        return JsonResponse({
            'success': True,
            'criados': criados,
            'existentes': existentes,
            'message': f'{criados} tipo(s) de risco criado(s). {existentes} já existiam.'
        })

class EntregasPorEquipamentoView(LoginRequiredMixin, View):
    """Retorna entregas ativas (não devolvidas) de um equipamento."""

    def get(self, request):
        equipamento_id = request.GET.get('equipamento_id')
        filial = request.user.filial_ativa

        if not equipamento_id:
            return JsonResponse({'entregas': []})

        entregas = EntregaEPI.objects.filter(
            filial=filial,
            equipamento_id=equipamento_id,
            data_devolucao__isnull=True  # ← "ativo" = não devolvido
        ).select_related('ficha__funcionario', 'equipamento')

        data = [
            {
                'id': e.pk,
                'texto': (
                    f"{e.ficha.funcionario.nome_completo} — "
                    f"Entregue em {e.data_entrega.strftime('%d/%m/%Y')}"
                    if e.ficha else str(e)
                )
            }
            for e in entregas
        ]

        return JsonResponse({'entregas': data})

