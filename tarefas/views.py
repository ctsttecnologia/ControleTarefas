# tarefas/views.py
"""
Matriz de permissões (regra única em tarefas/permissions.py):

| Ação     | Superuser | view_all | change | Criador | Responsável | Participante |
|----------|-----------|----------|--------|---------|-------------|--------------|
| Listar   | Sim       | Sim      | Sim    | Sim     | Sim         | Sim          |
| Ver      | Sim       | Sim      | Sim    | Sim     | Sim         | Sim          |
| Editar   | Sim       | Não      | Sim    | Sim     | Sim         | Não          |
| Concluir | Sim       | Não      | Não    | Sim     | Sim         | Não          |
| Excluir  | Sim       | Não      | Não    | Sim     | Não         | Não          |
| Comentar | Sim       | Sim      | Sim    | Sim     | Sim         | Sim          |
"""
import json
import logging
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Case, Count, IntegerField, When
from django.db.models.functions import TruncWeek
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)

from core.mixins import (
    AppPermissionMixin, FuncionarioRequiredMixin,
    TarefaAccessMixin, ViewFilialScopedMixin,
)
from notifications.services import notificar_tarefa_comentario

from . import permissions as perms
from .forms import ComentarioForm, TarefaForm
from .models import Comentario, HistoricoStatus, Tarefas
from .services import (
    gerar_csv_relatorio,
    gerar_docx_relatorio,
    gerar_pdf_relatorio,
    preparar_contexto_relatorio,
    registrar_alteracao_status,
)

User = get_user_model()
logger = logging.getLogger(__name__)

ORDEM_PRIORIDADE = Case(
    When(prioridade='alta', then=0),
    When(prioridade='media', then=1),
    When(prioridade='normal', then=2),
    When(prioridade='baixa', then=3),
    default=4,
    output_field=IntegerField(),
)


# =============================================================================
# HELPERS
# =============================================================================

def aplicar_filtro_visibilidade(queryset, user):
    """Mantido por compatibilidade; delega à regra única."""
    return perms.filtrar_visibilidade(queryset, user)


def _queryset_escopo(request):
    """Tarefas visíveis ao usuário na filial ativa (falha fechado)."""
    qs = perms.filtrar_por_filial(Tarefas.objects.all(), request)
    return perms.filtrar_visibilidade(qs, request.user)


def _aplicar_mudanca_status(tarefa, novo_status, user):
    """
    Altera o status sem disparar save() (evita histórico duplicado),
    registrando nos históricos v2 e legado.
    """
    status_anterior = tarefa.status

    registrar_alteracao_status(
        tarefa=tarefa,
        status_anterior_key=status_anterior,
        novo_status_key=novo_status,
        alterado_por=user,
    )

    campos = {'status': novo_status}
    if novo_status == 'concluida':
        campos['concluida_em'] = timezone.now()
    elif status_anterior == 'concluida':
        campos['concluida_em'] = None

    Tarefas.objects.filter(pk=tarefa.pk).update(**campos)

    try:
        HistoricoStatus.objects.create(
            tarefa=tarefa,
            status_anterior=status_anterior,
            novo_status=novo_status,
            alterado_por=user,
            filial=tarefa.filial,
        )
    except Exception:
        logger.warning('Falha ao gravar HistoricoStatus legado (tarefa=%s)', tarefa.pk, exc_info=True)

    return status_anterior


class TarefasBaseMixin(
    FuncionarioRequiredMixin,
    AppPermissionMixin,
    ViewFilialScopedMixin,
    TarefaAccessMixin,
):
    """Mixin base para todas as views de Tarefas."""
    app_label_required = 'tarefas'
    modulo_nome = 'Tarefas'


# =============================================================================
# CRUD
# =============================================================================

class TarefaListView(TarefasBaseMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/listar_tarefas.html'
    context_object_name = 'object_list'
    paginate_by = 20

    def _get_base_queryset(self):
        qs = super().get_queryset()
        return perms.filtrar_visibilidade(qs, self.request.user)

    def get_queryset(self):
        qs = self._get_base_queryset()
        g = self.request.GET

        if status := g.get('status'):
            qs = qs.filter(status=status)
        if projeto := g.get('projeto'):
            qs = qs.filter(projeto=projeto)
        if prioridade := g.get('prioridade'):
            qs = qs.filter(prioridade=prioridade)
        if responsavel := g.get('responsavel'):
            qs = qs.filter(responsavel_id=responsavel)
        if data_inicio := g.get('data_inicio'):
            qs = qs.filter(prazo__gte=data_inicio)
        if data_fim := g.get('data_fim'):
            qs = qs.filter(prazo__lte=data_fim)

        if query := g.get('q'):
            from django.db.models import Q
            qs = qs.filter(
                Q(titulo__icontains=query)
                | Q(descricao__icontains=query)
                | Q(projeto__icontains=query)
                | Q(responsavel__first_name__icontains=query)
                | Q(responsavel__last_name__icontains=query)
                | Q(responsavel__username__icontains=query)
                | Q(participantes__first_name__icontains=query)
                | Q(participantes__last_name__icontains=query)
                | Q(participantes__username__icontains=query)
            ).distinct()

        return (
            qs.select_related('usuario', 'responsavel', 'filial')
            .prefetch_related('participantes')
            .annotate(ordem_prioridade=ORDEM_PRIORIDADE)
            .order_by('-prazo', 'ordem_prioridade')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = self._get_base_queryset()
        agora = timezone.now()
        encerradas = ['concluida', 'cancelada']

        context['total_tarefas'] = base_qs.count()
        context['tarefas_concluidas'] = base_qs.filter(status='concluida').count()
        context['tarefas_pendentes'] = base_qs.exclude(status__in=encerradas).count()
        context['tarefas_atrasadas'] = (
            base_qs.filter(prazo__lt=agora).exclude(status__in=encerradas).count()
        )

        context['status_options'] = Tarefas.STATUS_CHOICES
        context['prioridade_options'] = Tarefas.PRIORIDADE_CHOICES

        projetos = (
            base_qs.exclude(projeto__isnull=True).exclude(projeto__exact='')
            .values_list('projeto', flat=True).distinct().order_by('projeto')
        )
        context['projeto_options'] = [(p, p) for p in projetos]

        # LGPD (minimização): só usuários da filial ativa
        qs_resp = User.objects.filter(is_active=True)
        filial_id = self.request.session.get('active_filial_id')
        if filial_id:
            qs_resp = qs_resp.filter(filiais_permitidas__id=filial_id)
        elif not self.request.user.is_superuser:
            qs_resp = qs_resp.none()
        context['responsaveis'] = qs_resp.distinct().order_by('first_name', 'last_name')

        g = self.request.GET
        context['responsavel_atual'] = g.get('responsavel', '')
        context['status_atual'] = g.get('status', '')
        context['projeto_atual'] = g.get('projeto', '')
        context['prioridade_atual'] = g.get('prioridade', '')
        context['query_atual'] = g.get('q', '')
        context['data_inicio_atual'] = g.get('data_inicio', '')
        context['data_fim_atual'] = g.get('data_fim', '')
        return context


@login_required
@require_POST
def concluir_tarefa_rapido(request, pk):
    """Conclusão em 1 clique: superuser, criador ou responsável."""
    tarefa = get_object_or_404(_queryset_escopo(request), pk=pk)
    destino = request.META.get('HTTP_REFERER', 'tarefas:listar_tarefas')

    if not perms.can_conclude(request.user, tarefa):
        messages.error(request, 'Você não tem permissão para concluir esta tarefa.')
        return redirect(destino)

    if tarefa.status != 'concluida':
        tarefa._alterado_por = request.user
        tarefa.status = 'concluida'
        tarefa.concluida_em = timezone.now()
        tarefa.save(update_fields=['status', 'concluida_em'])
        messages.success(request, f'Tarefa "{tarefa.titulo}" marcada como concluída.')
    else:
        messages.info(request, 'Esta tarefa já estava concluída.')

    return redirect(destino)


class TarefaDetailView(TarefasBaseMixin, DetailView):
    model = Tarefas
    template_name = 'tarefas/tarefa_detail.html'
    context_object_name = 'object'

    def get_queryset(self):
        return perms.filtrar_visibilidade(super().get_queryset(), self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tarefa = self.object
        user = self.request.user

        ctx['comentarios'] = tarefa.comentarios.select_related('autor').all()
        ctx['historicos'] = (
            tarefa.historicos_v2.select_related('alterado_por')
            .order_by('-data_alteracao')[:50]
        )
        ctx['form'] = ComentarioForm()
        ctx['status_choices'] = Tarefas.STATUS_CHOICES

        ctx['can_edit'] = perms.can_edit(user, tarefa)
        ctx['can_conclude'] = perms.can_conclude(user, tarefa)
        ctx['can_delete'] = perms.can_delete(user, tarefa)
        ctx['can_comment'] = perms.can_comment(user, tarefa)
        ctx['can_change_status'] = perms.can_edit(user, tarefa)

        ctx['today'] = timezone.localdate()
        return ctx

    def post(self, request, *args, **kwargs):
        """Comentar: qualquer pessoa que pode ver a tarefa."""
        self.object = self.get_object()
        if not perms.can_comment(request.user, self.object):
            raise PermissionDenied

        form = ComentarioForm(request.POST, request.FILES)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.tarefa = self.object
            comentario.autor = request.user
            comentario.filial = self.object.filial
            comentario.save()

            notificar_tarefa_comentario(
                tarefa=self.object,
                autor=request.user,
                texto_comentario=comentario.texto,
            )
            return redirect('tarefas:tarefa_detail', pk=self.object.pk)

        ctx = self.get_context_data()
        ctx['form'] = form
        return self.render_to_response(ctx)


class TarefaCreateView(TarefasBaseMixin, CreateView):
    model = Tarefas
    form_class = TarefaForm
    template_name = 'tarefas/tarefa_form.html'
    permission_required = 'tarefas.add_tarefas'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.filial = self.request.user.filial_ativa

        response = super().form_valid(form)
        self.object._alterado_por = self.request.user
        self.object.participantes.add(self.request.user)
        return response


class TarefaUpdateView(TarefasBaseMixin, UpdateView):
    model = Tarefas
    form_class = TarefaForm
    template_name = 'tarefas/tarefa_form.html'

    def get_queryset(self):
        return perms.filtrar_visibilidade(super().get_queryset(), self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not perms.can_edit(self.request.user, obj):
            raise PermissionDenied('Você não tem permissão para editar esta tarefa.')
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        # Antes de super(): disponível ao signal m2m_changed
        form.instance._alterado_por = self.request.user
        return super().form_valid(form)


class TarefaDeleteView(TarefasBaseMixin, DeleteView):
    model = Tarefas
    template_name = 'tarefas/confirmar_exclusao.html'
    success_url = reverse_lazy('tarefas:listar_tarefas')

    def get_queryset(self):
        return perms.filtrar_visibilidade(super().get_queryset(), self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not perms.can_delete(self.request.user, obj):
            raise PermissionDenied('Apenas o criador ou administrador pode excluir.')
        return obj

    def form_valid(self, form):
        logger.info(
            'EXCLUSAO tarefa=%s user=%s filial=%s',
            self.object.pk, self.request.user.pk, self.object.filial_id,
        )
        messages.success(self.request, 'Tarefa excluída com sucesso!')
        return super().form_valid(form)


# =============================================================================
# COMENTÁRIOS
# =============================================================================

def pode_excluir_comentario(user, comentario):
    return (
        user.is_superuser
        or user.has_perm('tarefas.delete_comentario')
        or comentario.autor_id == user.pk
    )


@login_required
@require_POST
def comentario_excluir(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if not pode_excluir_comentario(request.user, comentario):
        raise PermissionDenied

    if comentario.anexo:
        comentario.anexo.delete(save=False)

    tarefa_id = comentario.tarefa_id
    comentario.delete()
    return redirect('tarefas:tarefa_detail', pk=tarefa_id)


@login_required
@require_POST
def comentario_anexo_excluir(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if not pode_excluir_comentario(request.user, comentario):
        raise PermissionDenied

    if comentario.anexo:
        comentario.anexo.delete(save=False)
        comentario.save(update_fields=['anexo'])

    return redirect('tarefas:tarefa_detail', pk=comentario.tarefa_id)


class ConcluirTarefaView(TarefasBaseMixin, View):
    """Marca uma tarefa como concluída via POST."""

    def post(self, request, pk):
        tarefa = get_object_or_404(_queryset_escopo(request), pk=pk)
        if not perms.can_conclude(request.user, tarefa):
            raise PermissionDenied

        if tarefa.status != 'concluida':
            tarefa._alterado_por = request.user
            tarefa.status = 'concluida'
            tarefa.save()
            messages.success(request, f'Tarefa "{tarefa.titulo}" concluída!')
        else:
            messages.info(request, 'Esta tarefa já estava concluída.')

        return redirect('tarefas:listar_tarefas')


# =============================================================================
# KANBAN
# =============================================================================

class KanbanView(TarefasBaseMixin, TemplateView):
    template_name = 'tarefas/kanban_board.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        qs = _queryset_escopo(self.request).select_related('responsavel', 'usuario')

        responsavel_id = self.request.GET.get('responsavel')
        if responsavel_id:
            qs = qs.filter(responsavel_id=responsavel_id)

        responsaveis = User.objects.filter(
            pk__in=qs.values_list('responsavel', flat=True).distinct()
        ).order_by('first_name', 'username')

        ctx['colunas'] = [
            {'key': key, 'label': label, 'tarefas': qs.filter(status=key)}
            for key, label in Tarefas.STATUS_CHOICES
        ]
        ctx['status_choices'] = Tarefas.STATUS_CHOICES
        ctx['responsaveis'] = responsaveis
        ctx['responsavel_atual'] = responsavel_id or ''
        ctx['hoje'] = timezone.localdate()
        return ctx


@login_required
@require_POST
def update_task_status(request):
    """Endpoint AJAX do Kanban — mover tarefa entre colunas."""
    task_id = request.POST.get('task_id')
    new_status = request.POST.get('new_status', '').strip()

    if not task_id or not new_status:
        return JsonResponse({'success': False, 'message': 'Dados incompletos.'}, status=400)

    status_validos = dict(Tarefas.STATUS_CHOICES)
    if new_status not in status_validos:
        return JsonResponse(
            {'success': False, 'message': f'Status "{new_status}" inválido.'}, status=400
        )

    try:
        tarefa = _queryset_escopo(request).get(pk=task_id)
    except (Tarefas.DoesNotExist, ValueError):
        return JsonResponse(
            {'success': False, 'message': 'Tarefa não encontrada ou sem permissão.'}, status=404
        )

    if not perms.can_change_status(request.user, tarefa, new_status):
        return JsonResponse({'success': False, 'message': 'Sem permissão.'}, status=403)

    if tarefa.status == new_status:
        return JsonResponse({'success': True, 'changed': False})

    _aplicar_mudanca_status(tarefa, new_status, request.user)

    return JsonResponse({
        'success': True,
        'changed': True,
        'task_id': task_id,
        'new_status': new_status,
        'new_status_display': status_validos[new_status],
    })


# =============================================================================
# CALENDÁRIO
# =============================================================================

class CalendarioTarefasView(TarefasBaseMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/calendario.html'

    def get_queryset(self):
        qs = perms.filtrar_visibilidade(super().get_queryset(), self.request.user)
        return (
            qs.filter(prazo__isnull=False)
            .exclude(status='cancelada')
            .select_related('responsavel')
        )

    def _classe_css_evento(self, tarefa):
        hoje = timezone.now().date()
        prazo = tarefa.prazo.date() if hasattr(tarefa.prazo, 'date') else tarefa.prazo
        data_criacao = tarefa.data_criacao.date()

        if prazo < hoje:
            return 'fc-event-status-atrasada'
        if data_criacao >= hoje - timedelta(days=3):
            return 'fc-event-status-recente'
        if prazo <= hoje + timedelta(days=7):
            return 'fc-event-status-proximo-prazo'
        return 'fc-event-status-em-andamento'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        eventos = []

        for t in context['object_list']:
            try:
                prazo_fmt = t.prazo.strftime('%d/%m/%Y')
                eventos.append({
                    'start': t.data_criacao.strftime('%Y-%m-%d'),
                    'title': f'{t.titulo} (Prazo: {prazo_fmt})',
                    'url': reverse('tarefas:tarefa_detail', kwargs={'pk': t.pk}),
                    'className': f'fc-event-prioridade-{t.prioridade} {self._classe_css_evento(t)}',
                    'allDay': True,
                    'extendedProps': {
                        'status': t.status,
                        'data_criacao': t.data_criacao.strftime('%Y-%m-%d %H:%M'),
                        'prazo': prazo_fmt,
                    },
                })
            except Exception:
                logger.error('Erro ao processar tarefa %s', t.pk, exc_info=True)

        context['eventos_json'] = json.dumps(eventos)
        return context


# =============================================================================
# API legada — UpdateTaskStatusView
# =============================================================================

class UpdateTaskStatusView(TarefasBaseMixin, View):
    """API AJAX (drag & drop) — versão legada."""

    def post(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Requisição inválida.'}, status=400)

        task_id = request.POST.get('task_id')
        new_status = request.POST.get('new_status')

        if new_status not in dict(Tarefas.STATUS_CHOICES):
            return JsonResponse({'success': False, 'message': 'Status inválido.'}, status=400)

        try:
            tarefa = _queryset_escopo(request).get(pk=task_id)
        except (Tarefas.DoesNotExist, ValueError):
            return JsonResponse(
                {'success': False, 'message': 'Tarefa não encontrada ou sem permissão.'},
                status=404,
            )

        if not perms.can_change_status(request.user, tarefa, new_status):
            return JsonResponse({'success': False, 'message': 'Sem permissão.'}, status=403)

        try:
            tarefa._alterado_por = request.user
            tarefa.status = new_status
            tarefa.save()
            return JsonResponse({'success': True, 'message': 'Status atualizado.'})
        except Exception:
            logger.error('Erro ao atualizar tarefa %s', task_id, exc_info=True)
            return JsonResponse({'success': False, 'message': 'Erro interno.'}, status=500)


# =============================================================================
# RELATÓRIOS
# =============================================================================

def _build_queryset_relatorio(request):
    """Filial + visibilidade + filtros GET/POST. Usado pelas views de relatório."""
    qs = _queryset_escopo(request)
    params = request.POST if request.method == 'POST' else request.GET

    if status := params.get('status'):
        qs = qs.filter(status=status)
    if prioridade := params.get('prioridade'):
        qs = qs.filter(prioridade=prioridade)
    if responsavel := params.get('responsavel'):
        qs = qs.filter(responsavel_id=responsavel)
    if projeto := params.get('projeto'):
        qs = qs.filter(projeto=projeto)

    return qs.select_related('responsavel', 'filial').order_by('-data_criacao')


def _exportar_relatorio(request, formato):
    """Roteador de exportação (exige permissão + auditoria LGPD)."""
    if not (request.user.is_superuser or request.user.has_perm(perms.PERM_EXPORT)):
        raise PermissionDenied('Você não tem permissão para exportar relatórios.')

    exporters = {
        'pdf':  gerar_pdf_relatorio,
        'csv':  gerar_csv_relatorio,
        'docx': gerar_docx_relatorio,
        'xlsx': gerar_xlsx_relatorio,
    }
    exporter = exporters.get(formato)
    if not exporter:
        messages.error(request, 'Formato de exportação inválido.')
        return redirect('tarefas:relatorio_tarefas')

    qs = _build_queryset_relatorio(request)
    logger.info(
        'EXPORT tarefas formato=%s user=%s filial=%s registros=%s',
        formato, request.user.pk,
        request.session.get('active_filial_id'), qs.count(),
    )

    context = preparar_contexto_relatorio(qs)
    context['request'] = request
    context['now'] = timezone.now()
    context['data_emissao'] = timezone.now().strftime('%d/%m/%Y %H:%M')
    return exporter(context)


class RelatorioTarefasView(TarefasBaseMixin, ListView):
    """GET: tabela + gráficos + filtros. POST: exporta."""
    model = Tarefas
    template_name = 'tarefas/relatorio_tarefas.html'

    def get_queryset(self):
        return _build_queryset_relatorio(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context.update(preparar_contexto_relatorio(qs))

        context['status_data_json'] = json.dumps(
            context.get('status_data', []), cls=DjangoJSONEncoder
        )
        context['priority_data_json'] = json.dumps(
            context.get('prioridade_data', []), cls=DjangoJSONEncoder
        )
        context['status_choices'] = Tarefas.STATUS_CHOICES
        context['prioridade_choices'] = Tarefas.PRIORIDADE_CHOICES
        context['pode_exportar'] = (
            self.request.user.is_superuser
            or self.request.user.has_perm(perms.PERM_EXPORT)
        )

        base_qs = _queryset_escopo(self.request)
        context['responsaveis'] = User.objects.filter(
            pk__in=base_qs.values_list('responsavel', flat=True).distinct()
        ).order_by('first_name', 'username')

        g = self.request.GET
        context['current_filters'] = {
            'status': g.get('status', ''),
            'prioridade': g.get('prioridade', ''),
            'responsavel': g.get('responsavel', ''),
            'projeto': g.get('projeto', ''),
        }
        return context

    def post(self, request, *args, **kwargs):
        formato = request.POST.get('export_format')
        if not formato:
            return self.get(request, *args, **kwargs)
        return _exportar_relatorio(request, formato)


class ExportarRelatorioView(TarefasBaseMixin, View):
    """Exportação rápida via GET: /tarefas/relatorio/exportar/?formato=pdf"""

    def get(self, request, *args, **kwargs):
        return _exportar_relatorio(request, request.GET.get('formato', ''))


def gerar_xlsx_relatorio(context):
    """Gera o Excel do relatório (mesmo `context` dos demais exportadores)."""
    from openpyxl import Workbook
    from .utils.excel_styles import aplicar_cabecalho_relatorio, aplicar_estilo_tabela

    wb = Workbook()
    ws = wb.active
    ws.title = 'Relatório de Tarefas'

    headers = ['Qtda.', 'Título', 'Responsável', 'Status', 'Prioridade',
               'Projeto', 'Criação', 'Prazo']

    start_row = aplicar_cabecalho_relatorio(
        ws,
        titulo='Relatório de Tarefas',
        subtitulo='Acompanhamento e análise de tarefas do sistema',
        data_emissao=context.get('data_emissao', timezone.now().strftime('%d/%m/%Y %H:%M')),
        num_colunas=len(headers),
    )

    for col, h in enumerate(headers, start=1):
        ws.cell(row=start_row, column=col, value=h)

    tarefas = context.get('tarefas', [])
    for idx, t in enumerate(tarefas, start=1):
        row = start_row + idx
        ws.cell(row=row, column=1, value=idx)
        ws.cell(row=row, column=2, value=t.titulo)
        ws.cell(row=row, column=3, value=t.responsavel.get_full_name() if t.responsavel else '—')
        ws.cell(row=row, column=4, value=t.get_status_display())
        ws.cell(row=row, column=5, value=t.get_prioridade_display())
        ws.cell(row=row, column=6, value=str(t.projeto) if t.projeto else '—')
        ws.cell(row=row, column=7,
                value=t.data_criacao.strftime('%d/%m/%Y') if t.data_criacao else '—')
        ws.cell(row=row, column=8,
                value=t.prazo.strftime('%d/%m/%Y') if t.prazo else '—')

    aplicar_estilo_tabela(
        ws, header_row=start_row, total_rows=len(tarefas), total_cols=len(headers),
    )

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="relatorio_tarefas_{timezone.now():%Y%m%d_%H%M}.xlsx"'
    )
    wb.save(response)
    return response


# =============================================================================
# DASHBOARD ANALÍTICO
# =============================================================================

class DashboardAnaliticoView(TarefasBaseMixin, TemplateView):
    template_name = 'tarefas/dashboard.html'

    PERIODO_CHOICES = {'hoje': 0, '7d': 7, '30d': 30}

    def _get_periodo_datas(self):
        """Retorna (data_inicio, data_fim, periodo_label)."""
        periodo = self.request.GET.get('periodo', '30d')
        hoje = timezone.localdate()

        if periodo == 'custom':
            ini = self.request.GET.get('data_inicio')
            fim = self.request.GET.get('data_fim')
            try:
                data_inicio = date.fromisoformat(ini) if ini else hoje - timedelta(days=30)
                data_fim = date.fromisoformat(fim) if fim else hoje
            except ValueError:
                data_inicio, data_fim = hoje - timedelta(days=30), hoje
            return data_inicio, data_fim, 'custom'

        if periodo == 'hoje':
            return hoje, hoje, 'hoje'

        dias = self.PERIODO_CHOICES.get(periodo, 30)
        return hoje - timedelta(days=dias), hoje, periodo

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        user = request.user
        filial_id = request.session.get('active_filial_id')
        agora = timezone.now()
        hoje = timezone.localdate()
        encerradas = ['concluida', 'cancelada']

        data_inicio, data_fim, periodo_label = self._get_periodo_datas()

        base_qs = _queryset_escopo(request)
        periodo_qs = base_qs.filter(
            data_criacao__date__gte=data_inicio,
            data_criacao__date__lte=data_fim,
        )

        # ─── KPIs ───────────────────────────────────────────────
        total = base_qs.count()
        concluidas = base_qs.filter(status='concluida').count()
        pendentes = base_qs.filter(status='pendente').count()
        em_andamento = base_qs.filter(status='andamento').count()
        pausadas = base_qs.filter(status='pausada').count()
        atrasadas = base_qs.filter(prazo__lt=agora).exclude(status__in=encerradas).count()
        taxa_conclusao = round(concluidas / total * 100, 1) if total else 0

        criadas_periodo = periodo_qs.count()
        concluidas_periodo = periodo_qs.filter(status='concluida').count()
        taxa_periodo = (
            round(concluidas_periodo / criadas_periodo * 100, 1) if criadas_periodo else 0
        )

        fim_semana = hoje + timedelta(days=7)
        vence_hoje = base_qs.filter(prazo__date=hoje).exclude(status__in=encerradas).count()
        vence_semana = (
            base_qs.filter(prazo__date__gt=hoje, prazo__date__lte=fim_semana)
            .exclude(status__in=encerradas).count()
        )

        context.update({
            'total_tarefas': total,
            'tarefas_concluidas': concluidas,
            'tarefas_pendentes': pendentes,
            'tarefas_andamento': em_andamento,
            'tarefas_atrasadas': atrasadas,
            'tarefas_pausadas': pausadas,
            'taxa_conclusao': taxa_conclusao,
            'vence_hoje': vence_hoje,
            'vence_semana': vence_semana,
            'criadas_periodo': criadas_periodo,
            'concluidas_periodo': concluidas_periodo,
            'taxa_periodo': taxa_periodo,
            'periodo_atual': periodo_label,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        })

        # ─── Gráficos (cache coerente com a visibilidade) ───────
        visibilidade_key = 'all' if perms.can_view_all(user) else f'user{user.pk}'
        cache_key = f'dash_charts_{filial_id}_{visibilidade_key}_{data_inicio}_{data_fim}'
        charts_data = cache.get(cache_key)

        if charts_data is None:
            status_labels = dict(Tarefas.STATUS_CHOICES)
            prioridade_labels = dict(Tarefas.PRIORIDADE_CHOICES)

            status_counts = (
                base_qs.values('status')
                .annotate(total=Count('id', distinct=True)).order_by('status')
            )
            prioridade_counts = (
                base_qs.values('prioridade')
                .annotate(total=Count('id', distinct=True)).order_by('prioridade')
            )

            status_data = [
                {'status': status_labels.get(s['status'], s['status']),
                 'status_key': s['status'], 'total': s['total']}
                for s in status_counts
            ]
            prioridade_data = [
                {'prioridade': prioridade_labels.get(p['prioridade'], p['prioridade']),
                 'prioridade_key': p['prioridade'], 'total': p['total']}
                for p in prioridade_counts
            ]

            six_weeks_ago = agora - timedelta(weeks=6)
            criadas_qs = (
                base_qs.filter(data_criacao__gte=six_weeks_ago)
                .annotate(semana=TruncWeek('data_criacao')).values('semana')
                .annotate(total=Count('id', distinct=True)).order_by('semana')
            )
            concluidas_qs = (
                base_qs.filter(concluida_em__gte=six_weeks_ago, status='concluida')
                .annotate(semana=TruncWeek('concluida_em')).values('semana')
                .annotate(total=Count('id', distinct=True)).order_by('semana')
            )

            dados_criadas = {i['semana'].date(): i['total'] for i in criadas_qs}
            dados_concluidas = {i['semana'].date(): i['total'] for i in concluidas_qs}

            semana_inicio = hoje - timedelta(weeks=5)
            current_week = semana_inicio - timedelta(days=semana_inicio.weekday())

            tendencia_labels, criadas_list, concluidas_list = [], [], []
            while current_week <= hoje:
                tendencia_labels.append(current_week)
                criadas_list.append(dados_criadas.get(current_week, 0))
                concluidas_list.append(dados_concluidas.get(current_week, 0))
                current_week += timedelta(weeks=1)

            charts_data = {
                'tendencia_labels': tendencia_labels,
                'tendencia_criadas': criadas_list,
                'tendencia_concluidas': concluidas_list,
                'status_data': status_data,
                'prioridade_data': prioridade_data,
                'taxa_conclusao': taxa_conclusao,
            }
            cache.set(cache_key, charts_data, 60 * 8)

        context['status_data'] = charts_data['status_data']
        context['prioridade_data'] = charts_data['prioridade_data']
        context['charts_data_json'] = json.dumps(charts_data, cls=DjangoJSONEncoder)

        context['tarefas_recentes'] = base_qs.select_related(
            'responsavel', 'responsavel__funcionario'
        ).order_by('-data_criacao')[:5]

        # ─── Desempenho da equipe (LGPD: só com permissão) ──────
        pode_ver_equipe = user.is_superuser or user.has_perm(perms.PERM_EQUIPE)
        context['pode_ver_equipe'] = pode_ver_equipe
        context['usuarios_performance'] = []
        context['ranking_top5'] = []

        if pode_ver_equipe:
            thirty_days_ago = agora - timedelta(days=30)

            usuarios_qs = User.objects.filter(is_active=True)
            if filial_id:
                usuarios_qs = usuarios_qs.filter(filiais_permitidas__id=filial_id)
            usuarios_qs = usuarios_qs.select_related('funcionario').distinct()

            ativas_por_user = dict(
                base_qs.filter(status__in=['pendente', 'andamento', 'atrasada'])
                .values('responsavel_id')
                .annotate(total=Count('id', distinct=True))
                .values_list('responsavel_id', 'total')
            )
            concluidas_por_user = dict(
                base_qs.filter(status='concluida', concluida_em__gte=thirty_days_ago)
                .values('responsavel_id')
                .annotate(total=Count('id', distinct=True))
                .values_list('responsavel_id', 'total')
            )

            performance = []
            for usuario in usuarios_qs:
                ativas = ativas_por_user.get(usuario.pk, 0)
                concl = concluidas_por_user.get(usuario.pk, 0)
                if ativas == 0 and concl == 0:
                    continue

                funcionario = getattr(usuario, 'funcionario', None)
                foto_url = (
                    funcionario.foto_3x4.url
                    if funcionario and funcionario.foto_3x4 else None
                )
                total_trab = ativas + concl
                performance.append({
                    'id': usuario.pk,
                    'username': usuario.get_full_name() or usuario.username,
                    'foto_url': foto_url,
                    'tarefas_ativas': ativas,
                    'tarefas_concluidas_30d': concl,
                    'produtividade': round(concl / total_trab * 100, 1) if total_trab else 0,
                })

            performance.sort(key=lambda u: u['tarefas_concluidas_30d'], reverse=True)
            ranking_top5 = performance[:5]

            top5_ids = [u['id'] for u in ranking_top5]
            titulos_por_user = {}
            if top5_ids:
                itens = (
                    base_qs.filter(
                        responsavel_id__in=top5_ids,
                        status='concluida',
                        concluida_em__gte=thirty_days_ago,
                    )
                    .values('responsavel_id', 'titulo')
                    .order_by('-concluida_em')
                )
                for item in itens:
                    titulos_por_user.setdefault(item['responsavel_id'], []).append(item['titulo'])

            for u in ranking_top5:
                titulos = titulos_por_user.get(u['id'], [])
                u['tarefas_concluidas_titulos'] = titulos[:3]
                u['tarefas_concluidas_extra'] = max(len(titulos) - 3, 0)

            context['usuarios_performance'] = performance
            context['ranking_top5'] = ranking_top5

        context['hoje'] = hoje
        return context


# =============================================================================
# ADMIN (SUPERUSER)
# =============================================================================

class TarefaAdminListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Lista TODAS as tarefas (sem filtro de filial). Apenas superuser."""
    model = Tarefas
    template_name = 'tarefas/tarefas_admin.html'
    context_object_name = 'tarefas'
    ordering = ['-data_criacao']
    paginate_by = 50

    def test_func(self):
        return self.request.user.is_superuser


# =============================================================================
# ALTERAR STATUS — AJAX (página de detalhe)
# =============================================================================

@login_required
@require_POST
def alterar_status_tarefa(request, pk):
    tarefa = get_object_or_404(_queryset_escopo(request), pk=pk)

    novo_status = request.POST.get('status', '').strip()
    status_validos = dict(Tarefas.STATUS_CHOICES)
    if novo_status not in status_validos:
        return JsonResponse({'error': 'Status inválido.'}, status=400)

    if not perms.can_change_status(request.user, tarefa, novo_status):
        return JsonResponse({'error': 'Sem permissão.'}, status=403)

    if tarefa.status == novo_status:
        return JsonResponse({'error': 'A tarefa já possui este status.'}, status=400)

    status_anterior_display = tarefa.get_status_display()
    _aplicar_mudanca_status(tarefa, novo_status, request.user)
    tarefa.refresh_from_db()

    return JsonResponse({
        'ok': True,
        'novo_status': novo_status,
        'novo_status_display': tarefa.get_status_display(),
        'status_anterior_display': status_anterior_display,
        'progresso': tarefa.progresso,
        'data_atualizacao': tarefa.data_atualizacao.strftime('%d/%m/%Y %H:%M'),
    })
