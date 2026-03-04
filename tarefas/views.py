# tarefas/views.py
# tarefas/views.py

import json
import logging
from collections import defaultdict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q, Count
from django.db.models.functions import TruncWeek
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.views.generic.edit import FormMixin

from core.mixins import ViewFilialScopedMixin, TarefaPermissionMixin
from .forms import TarefaForm, ComentarioForm
from .models import Tarefas, HistoricoStatus
from .services import (
    preparar_contexto_relatorio,
    gerar_pdf_relatorio,
    gerar_csv_relatorio,
    gerar_docx_relatorio,
)
from notifications.services import enviar_email as enviar_email_tarefa
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie


User = get_user_model()
logger = logging.getLogger(__name__)


# =============================================================================
# CRUD
# =============================================================================

class TarefaListView(LoginRequiredMixin, ViewFilialScopedMixin, TarefaPermissionMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/listar_tarefas.html'
    context_object_name = 'object_list'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()

        status = self.request.GET.get('status', '')
        prioridade = self.request.GET.get('prioridade', '')
        query = self.request.GET.get('q', '')

        if status:
            qs = qs.filter(status=status)
        if prioridade:
            qs = qs.filter(prioridade=prioridade)
        if query:
            qs = qs.filter(
                Q(titulo__icontains=query) |
                Q(descricao__icontains=query) |
                Q(projeto__icontains=query)
            )

        return qs.select_related('usuario', 'responsavel', 'filial').order_by('-prazo', 'prioridade')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = super().get_queryset()

        context['total_tarefas'] = base_qs.count()
        context['tarefas_concluidas'] = base_qs.filter(status='concluida').count()
        context['tarefas_pendentes'] = base_qs.exclude(
            status__in=['concluida', 'cancelada']
        ).count()
        context['status_options'] = Tarefas.STATUS_CHOICES
        context['prioridade_options'] = Tarefas.PRIORIDADE_CHOICES

        return context


class TarefaDetailView(
    LoginRequiredMixin, ViewFilialScopedMixin,
    TarefaPermissionMixin, FormMixin, DetailView
):
    model = Tarefas
    template_name = 'tarefas/tarefa_detail.html'
    form_class = ComentarioForm

    def get_queryset(self):
        return super().get_queryset().select_related('usuario', 'responsavel', 'filial')

    def get_success_url(self):
        return reverse('tarefas:tarefa_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tarefa = self.get_object()
        context['form'] = self.get_form()
        context['comentarios'] = tarefa.comentarios.select_related('autor').order_by('-criado_em')
        context['historicos'] = tarefa.historicos.select_related('alterado_por').order_by('-data_alteracao')
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        return self.form_valid(form) if form.is_valid() else self.form_invalid(form)

    def form_valid(self, form):
        comentario = form.save(commit=False)
        comentario.tarefa = self.object
        comentario.autor = self.request.user
        comentario.filial_id = self.request.session.get('active_filial_id')
        comentario.save()
        messages.success(self.request, 'Comentário adicionado!')
        return super().form_valid(form)


class TarefaCreateView(
    LoginRequiredMixin, ViewFilialScopedMixin,
    TarefaPermissionMixin, CreateView
):
    model = Tarefas
    form_class = TarefaForm
    template_name = 'tarefas/tarefa_form.html'
    success_url = reverse_lazy('tarefas:kanban_board')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        filial_id = self.request.session.get('active_filial_id')
        if filial_id:
            form.instance.filial_id = filial_id

        response = super().form_valid(form)
        tarefa = self.object

        # Notifica responsável
        if tarefa.responsavel and tarefa.responsavel.email:
            enviar_email_tarefa(
                assunto=f"Nova tarefa: '{tarefa.titulo}'",
                template_texto='tarefas/emails/email_nova_tarefa.txt',
                template_html='tarefas/emails/email_nova_tarefa.html',
                contexto={'tarefa': tarefa, 'criador': self.request.user},
                destinatarios=[tarefa.responsavel.email],
            )

        messages.success(self.request, "Tarefa criada com sucesso!")
        return response


class TarefaUpdateView(
    LoginRequiredMixin, ViewFilialScopedMixin,
    TarefaPermissionMixin, UpdateView
):
    model = Tarefas
    form_class = TarefaForm
    template_name = 'tarefas/tarefa_form.html'
    context_object_name = 'tarefa'
    success_url = reverse_lazy('tarefas:listar_tarefas')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        # Captura status antes da edição
        status_anterior = Tarefas.objects.filter(
            pk=self.object.pk
        ).values_list('status', flat=True).first()

        response = super().form_valid(form)
        tarefa = self.object

        # Email é enviado pelo signal de HistoricoStatus, evitando duplicação
        messages.success(self.request, f"Tarefa '{tarefa.titulo}' atualizada!")
        return response


class TarefaDeleteView(
    LoginRequiredMixin, ViewFilialScopedMixin,
    TarefaPermissionMixin, DeleteView
):
    model = Tarefas
    template_name = 'tarefas/confirmar_exclusao.html'
    success_url = reverse_lazy('tarefas:listar_tarefas')

    def form_valid(self, form):
        messages.success(self.request, "Tarefa excluída com sucesso!")
        return super().form_valid(form)


class ConcluirTarefaView(LoginRequiredMixin, View):
    """Marca uma tarefa como concluída via POST."""

    def post(self, request, pk):
        filial_id = request.session.get('active_filial_id')
        query = Q(pk=pk) & (Q(usuario=request.user) | Q(responsavel=request.user))
        if filial_id:
            query &= Q(filial_id=filial_id)

        tarefa = get_object_or_404(Tarefas, query)

        if tarefa.status != 'concluida':
            tarefa._user = request.user
            tarefa.status = 'concluida'
            tarefa.save()
            messages.success(request, f'Tarefa "{tarefa.titulo}" concluída!')
        else:
            messages.info(request, 'Esta tarefa já estava concluída.')

        return redirect('tarefas:listar_tarefas')


# =============================================================================
# KANBAN E CALENDÁRIO
# =============================================================================
@method_decorator(ensure_csrf_cookie, name='dispatch')
class KanbanView(LoginRequiredMixin, ViewFilialScopedMixin, TarefaPermissionMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/kanban_board.html'
    context_object_name = 'tarefas'

    def get_queryset(self):
        active_statuses = ['pendente', 'atrasada', 'andamento', 'concluida', 'pausada']
        return super().get_queryset().filter(
            status__in=active_statuses
        ).select_related('responsavel')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        tarefas_por_status = defaultdict(list)
        for tarefa in self.object_list:
            status_coluna = 'atrasada' if tarefa.atrasada else tarefa.status
            tarefas_por_status[status_coluna].append(tarefa)

        colunas_ordem = ['pendente', 'atrasada', 'andamento', 'concluida', 'pausada']
        status_nomes = dict(Tarefas.STATUS_CHOICES)

        context['colunas'] = [
            {
                'id': status_id,
                'nome': status_nomes.get(status_id, status_id),
                'tarefas': sorted(
                    tarefas_por_status.get(status_id, []),
                    key=lambda t: (t.prazo is None, t.prazo)
                ),
            }
            for status_id in colunas_ordem
        ]
        context['now'] = timezone.now()
        return context


class CalendarioTarefasView(
    LoginRequiredMixin, ViewFilialScopedMixin,
    TarefaPermissionMixin, ListView
):
    model = Tarefas
    template_name = 'tarefas/calendario.html'

    def get_queryset(self):
        return super().get_queryset().filter(
            prazo__isnull=False
        ).exclude(
            status='cancelada'
        ).select_related('responsavel')

    def _classe_css_evento(self, tarefa):
        """Determina classe CSS com base na data."""
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

        for t in self.get_queryset():
            try:
                prazo_fmt = t.prazo.strftime('%d/%m/%Y')
                classe = self._classe_css_evento(t)
                eventos.append({
                    'start': t.data_criacao.strftime('%Y-%m-%d'),
                    'title': f'{t.titulo} (Prazo: {prazo_fmt})',
                    'url': reverse('tarefas:tarefa_detail', kwargs={'pk': t.pk}),
                    'className': f'fc-event-prioridade-{t.prioridade} {classe}',
                    'allDay': True,
                    'extendedProps': {
                        'status': t.status,
                        'data_criacao': t.data_criacao.strftime('%Y-%m-%d %H:%M'),
                        'prazo': prazo_fmt,
                    },
                })
            except Exception as e:
                logger.error(f"Erro ao processar tarefa {t.pk}: {e}")

        context['eventos_json'] = json.dumps(eventos)
        return context


# =============================================================================
# API E RELATÓRIOS
# =============================================================================

class UpdateTaskStatusView(LoginRequiredMixin, View):
    """API AJAX para atualizar status de tarefa (Kanban drag & drop)."""

    def post(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Requisição inválida.'}, status=400)

        task_id = request.POST.get('task_id')
        new_status = request.POST.get('new_status')
        filial_id = request.session.get('active_filial_id')

        # Valida status
        valid_statuses = [s[0] for s in Tarefas.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'message': 'Status inválido.'}, status=400)

        try:
            query = Q(pk=task_id) & (Q(usuario=request.user) | Q(responsavel=request.user))
            if filial_id:
                query &= Q(filial_id=filial_id)

            tarefa = Tarefas.objects.get(query)
            tarefa._user = request.user
            tarefa.status = new_status
            tarefa.save()

            return JsonResponse({'success': True, 'message': 'Status atualizado.'})
        except Tarefas.DoesNotExist:
            return JsonResponse(
                {'success': False, 'message': 'Tarefa não encontrada ou sem permissão.'},
                status=404,
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar tarefa {task_id}: {e}")
            return JsonResponse(
                {'success': False, 'message': 'Erro interno.'},
                status=500,
            )


class RelatorioTarefasView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/relatorio_tarefas.html'

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.GET.get('status') or self.request.POST.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-data_criacao')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        report_context = preparar_contexto_relatorio(qs)
        context.update(report_context)
        context['status_data_json'] = json.dumps(report_context.get('status_data', []))
        context['priority_data_json'] = json.dumps(report_context.get('prioridade_data', []))
        context['status_choices'] = Tarefas.STATUS_CHOICES
        context['current_filters'] = self.request.GET
        return context

    def post(self, request, *args, **kwargs):
        export_format = request.POST.get('export_format')
        if not export_format:
            return self.get(request, *args, **kwargs)

        qs = self.get_queryset()
        context = preparar_contexto_relatorio(qs)
        context['request'] = request

        exporters = {
            'pdf': gerar_pdf_relatorio,
            'csv': gerar_csv_relatorio,
            'docx': gerar_docx_relatorio,
        }
        exporter = exporters.get(export_format)
        if exporter:
            return exporter(context)

        return redirect('tarefas:relatorio_tarefas')


class DashboardAnaliticoView(
    LoginRequiredMixin, ViewFilialScopedMixin,
    TarefaPermissionMixin, TemplateView
):
    template_name = 'tarefas/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filial_id = self.request.session.get('active_filial_id')

        # Queryset base
        base_qs = Tarefas.objects.all()
        if filial_id:
            base_qs = base_qs.filter(filial_id=filial_id)

        usuarios = User.objects.filter(is_active=True)
        if filial_id:
            usuarios = usuarios.filter(filiais_permitidas__id=filial_id)

        # Performance dos usuários
        thirty_days_ago = timezone.now() - timedelta(days=30)
        usuarios_performance = []
        for usuario in usuarios:
            ativas = base_qs.filter(
                responsavel=usuario,
                status__in=['pendente', 'andamento', 'atrasada']
            ).count()
            concluidas = base_qs.filter(
                responsavel=usuario,
                status='concluida',
                concluida_em__gte=thirty_days_ago
            ).count()
            if ativas > 0 or concluidas > 0:
                usuarios_performance.append({
                    'username': usuario.get_full_name() or usuario.username,
                    'tarefas_ativas': ativas,
                    'tarefas_concluidas_30d': concluidas,
                })
        context['usuarios_performance'] = usuarios_performance

        # Gráfico de tendência (últimas 6 semanas)
        six_weeks_ago = timezone.now() - timedelta(weeks=6)

        criadas_qs = (
            base_qs.filter(data_criacao__gte=six_weeks_ago)
            .annotate(semana=TruncWeek('data_criacao'))
            .values('semana')
            .annotate(total=Count('id'))
            .order_by('semana')
        )
        concluidas_qs = (
            base_qs.filter(concluida_em__gte=six_weeks_ago, status='concluida')
            .annotate(semana=TruncWeek('concluida_em'))
            .values('semana')
            .annotate(total=Count('id'))
            .order_by('semana')
        )

        dados_criadas = {item['semana'].date(): item['total'] for item in criadas_qs}
        dados_concluidas = {item['semana'].date(): item['total'] for item in concluidas_qs}

        hoje = timezone.now().date()
        semana_inicio = hoje - timedelta(weeks=5)
        current_week = semana_inicio - timedelta(days=semana_inicio.weekday())

        labels, criadas_list, concluidas_list = [], [], []
        while current_week <= hoje:
            labels.append(current_week)
            criadas_list.append(dados_criadas.get(current_week, 0))
            concluidas_list.append(dados_concluidas.get(current_week, 0))
            current_week += timedelta(weeks=1)

        charts_data = {
            'tendencia_labels': labels,
            'tendencia_criadas': criadas_list,
            'tendencia_concluidas': concluidas_list,
            'performance_equipe': usuarios_performance,
        }
        context['charts_data_json'] = json.dumps(charts_data, cls=DjangoJSONEncoder)

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

