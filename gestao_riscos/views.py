
# gestao_riscos/views.py

import datetime
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView, CreateView, DeleteView, UpdateView, DetailView, TemplateView
)

from core.mixins import (
    AppPermissionMixin,
    ViewFilialScopedMixin,
    FilialCreateMixin,
    TecnicoScopeMixin,
)
from seguranca_trabalho.models import EntregaEPI

from .forms import IncidenteForm, InspecaoForm, CartaoTagForm, TipoRiscoForm
from .models import CartaoTag, Incidente, Inspecao, TipoRisco, CATEGORIA_RISCO_CHOICES


logger = logging.getLogger(__name__)
_APP = 'gestao_riscos'


# =============================================================================
# HELPER — Escopo de técnico reutilizável
# =============================================================================

def filtrar_queryset_por_tecnico(queryset, request, lookup_field):
    """
    Aplica o escopo de técnico a um queryset.
    - Se o user é técnico: filtra por lookup_field=user
    - Caso contrário: retorna queryset inalterado

    Substitui o anti-pattern de instanciar TecnicoScopeMixin() manualmente.
    """
    user = request.user
    if getattr(user, 'is_tecnico', False):
        return queryset.filter(**{lookup_field: user})
    return queryset


# =============================================================================
# DASHBOARD
# =============================================================================

class GestaoRiscosDashboardView(
    AppPermissionMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
    ListView
):
    """
    Dashboard que exibe dados de Gestão de Riscos, aplicando a
    arquitetura de segurança em 3 níveis.
    """
    app_label_required = _APP
    model = Incidente
    template_name = 'gestao_riscos/lista_riscos.html'
    context_object_name = 'incidentes'
    tecnico_scope_lookup = 'registrado_por'

    def get_queryset(self):
        return super().get_queryset().order_by('-data_ocorrencia')[:10]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Inspeções filtradas por filial via manager
        qs_inspecoes_base = Inspecao.objects.for_request(self.request)

        # Aplica escopo de técnico via função utilitária (sem instanciar mixin)
        qs_inspecoes_scoped = filtrar_queryset_por_tecnico(
            qs_inspecoes_base, self.request, 'responsavel'
        )

        context['inspecoes_pendentes'] = qs_inspecoes_scoped.filter(
            status='PENDENTE'
        ).order_by('data_agendada')

        context['inspecoes_propostas'] = qs_inspecoes_scoped.filter(
            status='PENDENTE_APROVACAO'
        ).order_by('data_agendada')

        context['titulo_pagina'] = 'Dashboard de Gestão de Riscos'
        return context


# =============================================================================
# INCIDENTES
# =============================================================================

class RegistrarIncidenteView(
    AppPermissionMixin,
    FilialCreateMixin,
    SuccessMessageMixin,
    CreateView
):
    app_label_required = _APP
    model = Incidente
    form_class = IncidenteForm
    template_name = 'gestao_riscos/registrar_incidente.html'
    success_url = reverse_lazy('gestao_riscos:lista_riscos')
    success_message = "Incidente registrado com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.registrado_por = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Registrar Novo Incidente'
        return context


# =============================================================================
# INSPEÇÕES
# =============================================================================

class AgendarInspecaoView(
    AppPermissionMixin,
    FilialCreateMixin,
    SuccessMessageMixin,
    CreateView
):
    app_label_required = _APP
    model = Inspecao
    form_class = InspecaoForm
    template_name = 'gestao_riscos/formulario_inspecao.html'
    success_url = reverse_lazy('gestao_riscos:calendario')
    success_message = "Inspeção agendada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        data_selecionada = self.request.GET.get('data')
        if data_selecionada:
            try:
                initial['data_agendada'] = datetime.date.fromisoformat(data_selecionada)
            except ValueError:
                pass
        initial['responsavel'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Agendar Nova Inspeção'
        return context


# =============================================================================
# CALENDÁRIO E API
# =============================================================================

class CalendarioView(AppPermissionMixin, TemplateView):
    """Renderiza a página principal do calendário."""
    app_label_required = _APP
    template_name = 'gestao_riscos/calendario.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Calendário de Inspeções'
        return context


class InspecaoEventsApiView(AppPermissionMixin, View):
    """
    Fornece os eventos de inspeção em formato JSON para o FullCalendar.
    Aplica os mesmos filtros de escopo que o dashboard.
    """
    app_label_required = _APP

    # Mapa de cores por status (fora do loop)
    CORES_POR_STATUS = {
        'CONCLUIDA': '#28a745',
        'PENDENTE_APROVACAO': '#ffc107',
        'PENDENTE': '#007bff',
    }

    def get(self, request, *args, **kwargs):
        # 1. Filtra pela Filial do usuário
        qs_base = Inspecao.objects.for_request(request)

        # 2. Filtra pelo escopo do Técnico (se aplicável)
        qs_scoped = filtrar_queryset_por_tecnico(qs_base, request, 'responsavel')

        # 3. Filtra por status visíveis + garante data preenchida
        qs_final = qs_scoped.filter(
            status__in=['PENDENTE', 'PENDENTE_APROVACAO', 'CONCLUIDA'],
            data_agendada__isnull=False,
        ).select_related('equipamento', 'responsavel')

        eventos = []
        for inspecao in qs_final:
            equipamento_nome = (
                inspecao.equipamento.nome if inspecao.equipamento else 'Inspeção'
            )
            responsavel_sufixo = (
                f" ({inspecao.responsavel.get_short_name()})"
                if inspecao.responsavel else ''
            )

            eventos.append({
                'id': inspecao.id,
                'title': f"{equipamento_nome}{responsavel_sufixo}",
                'start': inspecao.data_agendada.isoformat(),
                'url': inspecao.get_absolute_url(),
                'color': self.CORES_POR_STATUS.get(inspecao.status, '#6c757d'),
                'allDay': True,
            })

        return JsonResponse(eventos, safe=False)


class ListaInspecoesPropostasView(
    AppPermissionMixin,
    ViewFilialScopedMixin,
    ListView
):
    """
    Exibe inspeções propostas automaticamente (sem responsável confirmado ainda).
    TODOS os técnicos da filial podem ver — por isso NÃO usa TecnicoScopeMixin.
    """
    app_label_required = _APP
    model = Inspecao
    template_name = 'gestao_riscos/inspecoes_propostas_list.html'
    context_object_name = 'inspecoes_propostas'

    def get_queryset(self):
        return super().get_queryset().filter(
            status='PENDENTE_APROVACAO'
        ).order_by('data_agendada')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Confirmar Inspeções Propostas'
        return context


class ConfirmarInspecaoView(AppPermissionMixin, View):
    """View baseada em POST para confirmar uma inspeção proposta."""
    app_label_required = _APP
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        inspecao = get_object_or_404(
            Inspecao.objects.for_request(request),
            pk=pk,
            status='PENDENTE_APROVACAO'
        )

        inspecao.status = 'PENDENTE'
        inspecao.responsavel = request.user
        inspecao.save()

        messages.success(
            request,
            f"Inspeção para '{inspecao.equipamento}' confirmada e atribuída a você."
        )

        if 'next' in request.POST:
            return HttpResponseRedirect(request.POST.get('next'))
        return redirect('gestao_riscos:lista_inspecoes_propostas')


class InspecaoDetailView(
    AppPermissionMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
    DetailView
):
    """View de detalhe para a inspeção."""
    app_label_required = _APP
    model = Inspecao
    template_name = 'gestao_riscos/inspecao_detail.html'
    context_object_name = 'inspecao'
    tecnico_scope_lookup = 'responsavel'


class CompletarInspecaoView(
    AppPermissionMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
    SuccessMessageMixin,
    UpdateView
):
    """View para marcar uma inspeção como 'CONCLUÍDA'."""
    app_label_required = _APP
    model = Inspecao
    template_name = 'gestao_riscos/inspecao_completar_form.html'
    form_class = InspecaoForm
    success_url = reverse_lazy('gestao_riscos:calendario')
    success_message = "Inspeção marcada como Concluída!"
    tecnico_scope_lookup = 'responsavel'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.status = 'CONCLUIDA'
        if not form.instance.data_realizacao:
            form.instance.data_realizacao = timezone.now().date()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Concluir Inspeção: {self.object}"
        return context


# =============================================================================
# CARTÃO DE BLOQUEIO (TAG) — CRUD
# =============================================================================

class CartaoTagListView(
    AppPermissionMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
    ListView
):
    app_label_required = _APP
    model = CartaoTag
    template_name = 'gestao_riscos/cartao_tag_list.html'
    context_object_name = 'cartoes'
    paginate_by = 10
    tecnico_scope_lookup = 'responsavel'


class CartaoTagDetailView(
    AppPermissionMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
    DetailView
):
    app_label_required = _APP
    model = CartaoTag
    template_name = 'gestao_riscos/cartao_tag_detail.html'
    context_object_name = 'cartao'
    tecnico_scope_lookup = 'responsavel'


class CartaoTagCreateView(
    AppPermissionMixin,
    FilialCreateMixin,
    SuccessMessageMixin,
    CreateView
):
    app_label_required = _APP
    model = CartaoTag
    form_class = CartaoTagForm
    template_name = 'gestao_riscos/cartao_tag_form.html'
    success_url = reverse_lazy('gestao_riscos:cartao_tag_list')
    success_message = "Cartão de Bloqueio criado com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class CartaoTagUpdateView(
    AppPermissionMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
    SuccessMessageMixin,
    UpdateView
):
    app_label_required = _APP
    model = CartaoTag
    form_class = CartaoTagForm
    template_name = 'gestao_riscos/cartao_tag_form.html'
    success_url = reverse_lazy('gestao_riscos:cartao_tag_list')
    success_message = "Cartão de Bloqueio atualizado com sucesso!"
    tecnico_scope_lookup = 'responsavel'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class CartaoTagDeleteView(
    AppPermissionMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
    SuccessMessageMixin,
    DeleteView
):
    app_label_required = _APP
    model = CartaoTag
    template_name = 'gestao_riscos/cartao_tag_confirm_delete.html'
    success_url = reverse_lazy('gestao_riscos:cartao_tag_list')
    success_message = "Cartão de Bloqueio deletado com sucesso!"
    tecnico_scope_lookup = 'responsavel'


# =============================================================================
# TIPO DE RISCO — CRUD
# =============================================================================

class TipoRiscoListView(AppPermissionMixin, ViewFilialScopedMixin, ListView):
    """Lista de Tipos de Riscos — filtrada por filial."""
    app_label_required = _APP
    model = TipoRisco
    template_name = 'gestao_riscos/tipo_risco_list.html'
    context_object_name = 'tipos_risco'
    paginate_by = 20

    def get_queryset(self):
        # ✅ Usa super() que já vem filtrado por filial via ViewFilialScopedMixin
        qs = super().get_queryset()

        categoria = self.request.GET.get('categoria')
        if categoria:
            qs = qs.filter(categoria=categoria)

        ativo = self.request.GET.get('ativo')
        if ativo == 'true':
            qs = qs.filter(ativo=True)
        elif ativo == 'false':
            qs = qs.filter(ativo=False)

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

        todos = TipoRisco.objects.for_request(self.request)
        context['total_tipos'] = todos.count()
        context['total_ativos'] = todos.filter(ativo=True).count()

        contagem = dict(
            todos.values('categoria')
            .annotate(total=Count('id'))
            .values_list('categoria', 'total')
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


class TipoRiscoCreateView(
    AppPermissionMixin,
    FilialCreateMixin,
    SuccessMessageMixin,
    CreateView
):
    """Cadastrar novo Tipo de Risco."""
    app_label_required = _APP
    model = TipoRisco
    form_class = TipoRiscoForm
    template_name = 'gestao_riscos/tipo_risco_form.html'
    success_url = reverse_lazy('gestao_riscos:tipo_risco_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial'] = self.request.user.filial_ativa
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Tipo de Risco "{form.instance.nome}" cadastrado com sucesso!'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo Tipo de Risco'
        context['btn_texto'] = 'Cadastrar'
        context['cores_categorias'] = TipoRisco.CORES_CATEGORIA
        return context


class TipoRiscoUpdateView(
    AppPermissionMixin,
    ViewFilialScopedMixin,
    SuccessMessageMixin,
    UpdateView
):
    """Editar Tipo de Risco."""
    app_label_required = _APP
    model = TipoRisco
    form_class = TipoRiscoForm
    template_name = 'gestao_riscos/tipo_risco_form.html'
    success_url = reverse_lazy('gestao_riscos:tipo_risco_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial'] = self.request.user.filial_ativa
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Tipo de Risco "{form.instance.nome}" atualizado com sucesso!'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Tipo de Risco'
        context['btn_texto'] = 'Salvar Alterações'
        context['cores_categorias'] = TipoRisco.CORES_CATEGORIA
        return context


class TipoRiscoDeleteView(
    AppPermissionMixin,
    ViewFilialScopedMixin,
    SuccessMessageMixin,
    DeleteView
):
    """Excluir Tipo de Risco."""
    app_label_required = _APP
    model = TipoRisco
    template_name = 'gestao_riscos/tipo_risco_confirm_delete.html'
    success_url = reverse_lazy('gestao_riscos:tipo_risco_list')
    success_message = "Tipo de Risco excluído com sucesso!"

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Tipo de Risco "{self.object.nome}" excluído com sucesso!'
        )
        return super().form_valid(form)


class TipoRiscoToggleAtivoView(AppPermissionMixin, View):
    """Toggle ativo/inativo via AJAX — filtrado por filial."""
    app_label_required = _APP

    def post(self, request, pk):
        # ✅ Filtra por filial antes de buscar
        tipo = get_object_or_404(
            TipoRisco.objects.for_request(request),
            pk=pk
        )
        tipo.ativo = not tipo.ativo
        tipo.save(update_fields=['ativo'])

        return JsonResponse({
            'success': True,
            'ativo': tipo.ativo,
            'message': (
                f'"{tipo.nome}" '
                f'{"ativado" if tipo.ativo else "inativado"} com sucesso!'
            )
        })


class TipoRiscoPopularView(AppPermissionMixin, View):
    """Popular tipos de risco padrão para a filial (dados iniciais)."""
    app_label_required = _APP

    # Configuração fora do método — mais limpo e permite cachear
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

    def post(self, request):
        filial = request.user.filial_ativa

        if not filial:
            return JsonResponse({
                'success': False,
                'error': 'Nenhuma filial ativa selecionada.'
            }, status=400)

        criados = 0
        existentes = 0

        for categoria, info in self.RISCOS_PADRAO.items():
            for agente_nome, nr_ref in info['agentes']:
                _, created = TipoRisco.objects.get_or_create(
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


# =============================================================================
# API — ENTREGAS POR EQUIPAMENTO
# =============================================================================

class EntregasPorEquipamentoView(LoginRequiredMixin, AppPermissionMixin, View):
    """
    Retorna entregas ativas (não devolvidas) de um equipamento.
    Usa app_label de seguranca_trabalho pois consulta EntregaEPI.
    """
    app_label_required = 'seguranca_trabalho'

    def get(self, request):
        equipamento_id = request.GET.get('equipamento_id')
        filial = request.user.filial_ativa

        if not equipamento_id or not filial:
            return JsonResponse({'entregas': []})

        entregas = EntregaEPI.objects.filter(
            filial=filial,
            equipamento_id=equipamento_id,
            data_devolucao__isnull=True,
        ).select_related('ficha__funcionario', 'equipamento')

        data = [
            {
                'id': e.pk,
                'texto': (
                    f"{e.ficha.funcionario.nome_completo} — "
                    f"Entregue em {e.data_entrega.strftime('%d/%m/%Y')}"
                    if e.ficha else str(e)
                ),
            }
            for e in entregas
        ]

        return JsonResponse({'entregas': data})


