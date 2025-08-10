# tarefas/views.py

# Imports Padrão
import json
import logging
from collections import defaultdict
from datetime import timedelta

# Imports do Django
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Count, OuterRef, Subquery, IntegerField
from django.db.models.functions import TruncWeek
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormMixin
from requests import request

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .utils import enviar_email_notificacao_status # Importa a função


# Imports Locais
from .models import Tarefas, Comentario, HistoricoStatus
from .forms import TarefaForm, ComentarioForm
from .services import preparar_contexto_relatorio, gerar_pdf_relatorio, gerar_csv_relatorio, gerar_docx_relatorio
from core.mixins import FilialScopedQuerysetMixin, TarefaPermissionMixin


User = get_user_model()
logger = logging.getLogger(__name__)


# =============================================================================
# == VIEWS DE GERENCIAMENTO (CRUD)
# =============================================================================

class TarefaListView(LoginRequiredMixin, FilialScopedQuerysetMixin, TarefaPermissionMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/listar_tarefas.html'
    context_object_name = 'tarefas'
    paginate_by = 15

    def get_queryset(self):
        return super().get_queryset().order_by('-prazo', '-prioridade')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Tarefas.STATUS_CHOICES
        context['prioridade_choices'] = Tarefas.PRIORIDADE_CHOICES
        return context

class TarefaDetailView(LoginRequiredMixin, FilialScopedQuerysetMixin, TarefaPermissionMixin, FormMixin, DetailView):
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

class TarefaCreateView(LoginRequiredMixin, CreateView):
    model = Tarefas
    form_class = TarefaForm
    template_name = 'tarefas/criar_tarefa.html'
    success_url = reverse_lazy('tarefas:listar_tarefas')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        tarefa = form.save(commit=False)
        tarefa.usuario = self.request.user
        tarefa.filial_id = self.request.session.get('active_filial_id')
        tarefa.save()
        messages.success(self.request, "Tarefa criada com sucesso!")
        return redirect(self.success_url)

class TarefaUpdateView(LoginRequiredMixin, FilialScopedQuerysetMixin, TarefaPermissionMixin, UpdateView):
    model = Tarefas
    form_class = TarefaForm
    template_name = 'tarefas/editar_tarefa.html'
    context_object_name = 'tarefa'
    success_url = reverse_lazy('tarefas:listar_tarefas')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """
        Este método é chamado quando o formulário é válido.
        É o local perfeito para nossa lógica de notificação.
        """
        # 1. Captura o objeto da tarefa *antes* de qualquer alteração ser salva.
        tarefa_antes_da_edicao = self.get_object()
        status_anterior = tarefa_antes_da_edicao.get_status_display()

        # 2. Verifica se o campo 'status' realmente mudou.
        if 'status' in form.changed_data:
            novo_status = form.cleaned_data['status']
            novo_status_display = dict(Tarefas.STATUS_CHOICES).get(novo_status)
            
            # Chama a função para enviar o e-mail, se o status mudou.
            # Notifica o responsável pela tarefa.
            if status_anterior != novo_status_display and tarefa_antes_da_edicao.responsavel:
                enviar_email_notificacao_status(
                    tarefa=tarefa_antes_da_edicao,
                    usuario_notificado=tarefa_antes_da_edicao.responsavel,
                    status_anterior=status_anterior,
                    novo_status=novo_status_display,
                    request=self.request
                )
        
        # 3. Adiciona uma mensagem de sucesso para o usuário.
        messages.success(self.request, f"Tarefa '{self.get_object().titulo}' atualizada com sucesso!")

        # 4. Chama o método original da classe pai para salvar o objeto e redirecionar.
        return super().form_valid(form)

class TarefaDeleteView(LoginRequiredMixin, FilialScopedQuerysetMixin, UserPassesTestMixin, DeleteView):
    model = Tarefas
    template_name = 'tarefas/confirmar_exclusao.html'
    success_url = reverse_lazy('tarefas:listar_tarefas')

    def test_func(self):
        return self.request.user == self.get_object().usuario

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Tarefa excluída com sucesso!")
        return response

# =============================================================================
# == VIEWS DE VISUALIZAÇÃO (KANBAN, CALENDÁRIO)
# =============================================================================

class KanbanView(LoginRequiredMixin, FilialScopedQuerysetMixin, TarefaPermissionMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/kanban_board.html'
    context_object_name = 'tarefas' # Definir isso é uma boa prática em ListView

    def get_queryset(self):
        """Filtra apenas as tarefas ativas para o quadro Kanban."""
        # Adicionei 'concluida' para ter a coluna "Feito", que é comum em Kanbans.
        # Se não quiser, pode remover.
        active_statuses = ['pendente', 'andamento', 'pausada', 'atrasada', 'concluida']
        return super().get_queryset().filter(status__in=active_statuses)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Agrupa tarefas por status, movendo as atrasadas para uma categoria própria.
        tarefas_por_status = defaultdict(list)
        # O queryset já está disponível em context['tarefas'] ou self.object_list
        for tarefa in self.object_list: 
            # Se a tarefa estiver atrasada, ela vai para a coluna 'atrasada'.
            if tarefa.atrasada:
                status_coluna = 'atrasada'
            else:
                status_coluna = tarefa.status
            tarefas_por_status[status_coluna].append(tarefa)
            
        # 2. Define a ordem e o conteúdo das colunas
        # A ordem aqui define a ordem de exibição na tela.
        colunas_ordenadas = ['pendente', 'andamento', 'pausada', 'atrasada', 'concluida']
        status_nomes = dict(Tarefas.STATUS_CHOICES)

        colunas_finais = []
        for status_id in colunas_ordenadas:
            tarefas_da_coluna = tarefas_por_status.get(status_id, [])
            # Ordena as tarefas da coluna por prazo (as sem prazo vão para o fim)
            tarefas_ordenadas = sorted(
                tarefas_da_coluna, 
                key=lambda t: (t.prazo is None, t.prazo) # Ordenação mais robusta
            )
            colunas_finais.append({
                'id': status_id,
                'nome': status_nomes.get(status_id),
                'tarefas': tarefas_ordenadas
            })
        
        context['colunas'] = colunas_finais
        context['now'] = timezone.now() # Necessário para os badges no template
        return context
    
def enviar_email_notificacao(tarefa, usuario, status_anterior, novo_status, request):
    assunto = f"Atualização na Tarefa: {tarefa.titulo}"
    contexto = {
        'tarefa': tarefa,
        'usuario': usuario,
        'status_anterior': status_anterior,
        'novo_status': novo_status,
        'request': request, # Passa o request para gerar URLs completas
    }

    # Renderiza as duas versões do e-mail
    corpo_texto = render_to_string('tarefas/email_notificacao_status.txt', contexto)
    corpo_html = render_to_string('tarefas/email_notificacao_status.html', contexto)

    # Cria o e-mail e anexa a versão HTML
    email = EmailMultiAlternatives(
        subject=assunto,
        body=corpo_texto,
        from_email='seu-email@seudominio.com',
        to=[usuario.email]
    )
    email.attach_alternative(corpo_html, "text/html")
    email.send()

class CalendarioTarefasView(LoginRequiredMixin, FilialScopedQuerysetMixin, TarefaPermissionMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/calendario.html'

    def get_queryset(self):
        return super().get_queryset().filter(prazo__isnull=False).exclude(status__in=['concluida', 'cancelada'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        eventos = [
            {'title': t.titulo, 'start': t.prazo.isoformat(), 'url': reverse('tarefas:tarefa_detail', kwargs={'pk': t.pk}), 'className': f'fc-event-prioridade-{t.prioridade}'}
            for t in self.get_queryset()
        ]
        context['eventos_json'] = json.dumps(eventos)
        return context

# =============================================================================
# == VIEWS DE API E RELATÓRIOS
# =============================================================================

class UpdateTaskStatusView(LoginRequiredMixin, View):
    """
    Endpoint de API (AJAX) para atualizar o status de uma tarefa.
    """
    def post(self, request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Requisição inválida.'}, status=400)

        task_id = request.POST.get('task_id')
        new_status = request.POST.get('new_status')
        active_filial_id = request.session.get('active_filial_id')

        try:
            query = Q(pk=task_id) & (Q(usuario=request.user) | Q(responsavel=request.user))
            if not (request.user.is_superuser and not active_filial_id):
                 query &= Q(filial_id=active_filial_id)

            tarefa = Tarefas.objects.get(query)
            tarefa._user = request.user
            tarefa.status = new_status
            tarefa.save()
            return JsonResponse({'success': True, 'message': 'Status atualizado com sucesso.'})
        except Tarefas.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Tarefa não encontrada ou sem permissão.'}, status=404)
        except Exception as e:
            logger.error(f"Erro ao atualizar status da tarefa {task_id}: {e}")
            return JsonResponse({'success': False, 'message': 'Ocorreu um erro interno.'}, status=500)

class RelatorioTarefasView(LoginRequiredMixin, FilialScopedQuerysetMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/relatorio_tarefas.html'
    
    def get_queryset(self):
        qs = super().get_queryset().order_by('-data_criacao')
        status_filter = self.request.GET.get('status', self.request.POST.get('status', ''))
        return qs.filter(status=status_filter) if status_filter else qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        
        # Prepara dados para os gráficos e tabelas
        report_context = preparar_contexto_relatorio(queryset)
        context.update(report_context)
        
        # Prepara dados JSON para os gráficos
        status_data_list = report_context.get('status_data', [])
        # ... (lógica de formatação de timedelta que você já tinha) ...
        context['status_data_json'] = json.dumps(status_data_list)
        context['priority_data_json'] = json.dumps(report_context.get('prioridade_data', []))
        
        context['status_choices'] = Tarefas.STATUS_CHOICES
        context['current_filters'] = self.request.GET
        return context

    def post(self, request, *args, **kwargs):
        export_format = request.POST.get('export_format')
        if not export_format:
            # Se não for uma exportação, renderiza a página normalmente (com filtros POST)
            return self.get(request, *args, **kwargs)

        queryset = self.get_queryset()
        context = preparar_contexto_relatorio(queryset)
        context['request'] = request
        
        if export_format == 'pdf':
            return gerar_pdf_relatorio(context)
        elif export_format == 'csv':
            return gerar_csv_relatorio(context)
        elif export_format == 'docx':
            return gerar_docx_relatorio(context)
        
        return redirect('tarefas:relatorio_tarefas')

class DashboardAnaliticoView(LoginRequiredMixin, TemplateView):
    """
    Exibe o dashboard analítico com gráficos e métricas sobre as tarefas da filial.
    """
    template_name = 'tarefas/dashboard_analitico.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 1. Obtém a queryset base de tarefas já filtrada pela filial.
        #    Usamos o manager diretamente, pois TemplateView não tem `self.model`.
        try:
            tarefas_da_filial = Tarefas.objects.for_request(self.request)
        except AttributeError:
            # Fallback caso o manager .for_request não exista, evitando crashes.
            tarefas_da_filial = Tarefas.objects.none()

        hoje = timezone.now()
        trinta_dias_atras = hoje - timedelta(days=30)
        
        # 2. As queries agora partem da queryset já filtrada
        concluidas_30d = tarefas_da_filial.filter(
            responsavel=OuterRef('pk'),
            status='concluida',
            concluida_em__gte=trinta_dias_atras
        ).values('responsavel').annotate(c=Count('pk')).values('c')

        ativas = tarefas_da_filial.filter(
            responsavel=OuterRef('pk')
        ).exclude(status__in=['concluida', 'cancelada']).values('responsavel').annotate(c=Count('pk')).values('c')

        # Agora a variável 'User' está definida corretamente no escopo do módulo.
        usuarios = User.objects.filter(
            Q(tarefas_criadas__in=tarefas_da_filial) | Q(tarefas_responsavel__in=tarefas_da_filial)
        ).distinct().annotate(
            tarefas_concluidas_30d=Subquery(concluidas_30d, output_field=IntegerField(default=0)),
            tarefas_ativas=Subquery(ativas, output_field=IntegerField(default=0)),
        ).order_by('-tarefas_ativas')
        
        # O resto das queries também deve usar a queryset filtrada
        status_dist = list(tarefas_da_filial.values('status').annotate(total=Count('id')))
        prioridade_dist = list(tarefas_da_filial.values('prioridade').annotate(total=Count('id')))
        
        context['usuarios_performance'] = usuarios
        context['charts_data_json'] = json.dumps({
            'status_dist': status_dist,
            'prioridade_dist': prioridade_dist,
            # ... adicione outros dados de gráfico aqui
        }, default=str)
        
        return context
# =============================================================================
# == VIEW DE ADMIN (SUPERUSER)
# =============================================================================

class TarefaAdminListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Lista TODAS as tarefas de TODAS as filiais. Acesso restrito a superusuários.
    NÃO USA o escopo de filial.
    """
    model = Tarefas
    template_name = 'tarefas/tarefas.html'
    context_object_name = 'tarefas'
    ordering = ['-data_criacao']

    def test_func(self):
        return self.request.user.is_superuser

