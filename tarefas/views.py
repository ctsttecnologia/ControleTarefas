
from multiprocessing import context
from django.db import models 
from django.db.models import Count, Q, Avg, Subquery, OuterRef # Adicionado Subquery e OuterRef
from django.db.models.functions import TruncWeek # Adicionado TruncWeek

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin, PermissionRequiredMixin
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.dateparse import parse_date
from django.views.generic import View, TemplateView, ListView, UpdateView
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.template.loader import get_template
from xhtml2pdf import pisa

# Para geração de DOCX
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from .models import Tarefas, User, HistoricoStatus, Comentario 
from .forms import TarefaForm, ComentarioForm
from decimal import Decimal
from datetime import datetime, timedelta
from .reports import gerar_relatorio_tarefas
from collections import defaultdict
from .services import preparar_contexto_relatorio, gerar_pdf_relatorio, gerar_csv_relatorio, gerar_docx_relatorio

import usuario
import io
import os
import json
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# --- VIEWS DE ADMIN/GERENCIAIS ---
@login_required
def tarefas(request):
    """Lista todas as tarefas (apenas para superusuário)"""
    if not request.user.is_superuser:
        return redirect('tarefas:listar_tarefas')
    tarefas_list = Tarefas.objects.all().order_by('-data_criacao')
    return render(request, 'tarefas/tarefas.html', {'tarefas': tarefas_list})

# --- VIEWS DE CRUD (Create, Read, Update, Delete) ---

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
        messages.success(self.request, "Tarefa criada com sucesso!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Por favor, corrija os erros no formulário.")
        return super().form_invalid(form)

class TarefaUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Tarefas
    form_class = TarefaForm
    template_name = 'tarefas/editar_tarefa.html'
    context_object_name = 'tarefa'  

    def get_success_url(self):
        # Redireciona para a página de detalhes da tarefa editada
        return reverse_lazy('tarefas:tarefa_detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        # Garante que o criador ou o responsável edite a tarefa
        tarefa = self.get_object()
        return self.request.user == tarefa.usuario or self.request.user == tarefa.responsavel

    def get_form_kwargs(self):
        # Passa o 'request' para o formulário
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Tarefa atualizada com sucesso!")
        return super().form_valid(form)
    
# CORREÇÃO: Removido o decorator e adicionado LoginRequiredMixin
class TarefaDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Tarefas
    template_name = 'tarefas/confirmar_exclusao.html'
    success_url = reverse_lazy('tarefas:listar_tarefas')

    def test_func(self):
        # Permite que apenas o criador exclua a tarefa
        tarefa = self.get_object()
        return self.request.user == tarefa.usuario

    def form_valid(self, form):
        # O método delete é chamado por padrão, então adicionamos a mensagem aqui
        response = super().form_valid(form)
        messages.success(self.request, "Tarefa excluída com sucesso!")
        return response

@login_required
def listar_tarefas(request):
    # Lógica de listagem e filtros (pode ser convertida para ListView no futuro)
    tarefas_list = Tarefas.objects.filter(
        Q(usuario=request.user) | Q(responsavel=request.user)
    ).distinct().order_by('-data_criacao')
    
    context = {
        'tarefas': tarefas_list,
        'status_choices': Tarefas.STATUS_CHOICES,
        'prioridade_choices': Tarefas.PRIORIDADE_CHOICES,
    }
    return render(request, 'tarefas/listar_tarefas.html', context)

@login_required
def tarefa_detail(request, pk):
    # SUGESTÃO: Permite que o criador ou o responsável vejam os detalhes
    tarefa = get_object_or_404(Tarefas.objects.select_related('usuario', 'responsavel'), 
                               Q(pk=pk), 
                               Q(usuario=request.user) | Q(responsavel=request.user))
    
    comentarios = tarefa.comentarios.all().order_by('-criado_em')
    form = ComentarioForm()

    if request.method == 'POST':
        form = ComentarioForm(request.POST, request.FILES)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.tarefa = tarefa
            comentario.autor = request.user
            comentario.save()
            messages.success(request, 'Comentário adicionado!')
            return redirect('tarefas:tarefa_detail', pk=pk)

    context = {
        'tarefa': tarefa,
        'form': form,
        'comentarios': comentarios,
        'historicos': tarefa.historicos.all()
    }
    return render(request, 'tarefas/tarefa_detail.html', context)

# --- VIEWS DE FUNCIONALIDADES (Kanban, Calendário, etc.) ---

class KanbanView(LoginRequiredMixin, TemplateView):
    template_name = 'tarefas/kanban_board.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status_visiveis = ['pendente', 'andamento', 'pausada']
        
        tarefas = Tarefas.objects.filter(
            responsavel=self.request.user, 
            status__in=status_visiveis + ['atrasada']
        ).exclude(status__in=['concluida', 'cancelada'])

        tarefas_por_status = defaultdict(list)
        now = timezone.now()

        for tarefa in tarefas:
            if tarefa.atrasada:
                tarefas_por_status['atrasada'].append(tarefa)
            else:
                tarefas_por_status[tarefa.status].append(tarefa)
        
        colunas_visiveis = status_visiveis + ['atrasada']
        context['colunas'] = [
            {
                'id': status,
                'nome': dict(Tarefas.STATUS_CHOICES)[status],
                'tarefas': sorted(tarefas_por_status.get(status, []), key=lambda t: t.prazo or (now + timedelta(days=999)))
            }
            for status in colunas_visiveis
        ]
        return context

@login_required
def calendario_tarefas(request):
    tarefas_calendario = Tarefas.objects.filter(
        responsavel=request.user, 
        prazo__isnull=False
    ).exclude(status__in=['concluida', 'cancelada'])
    
    eventos = [
        {
            'title': tarefa.titulo,
            'start': tarefa.prazo.isoformat(),
            'url': reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk}),
            'className': f'fc-event-prioridade-{tarefa.prioridade}'
        }
        for tarefa in tarefas_calendario
    ]
    return render(request, 'tarefas/calendario.html', {'eventos_json': json.dumps(eventos)})

# --- VIEWS DE API/AJAX ---

@require_POST
@login_required
def update_task_status(request):
    # CORREÇÃO: Substituído request.is_ajax()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST' and is_ajax:
        task_id = request.POST.get('task_id')
        new_status = request.POST.get('new_status')
        
        try:
            tarefa = get_object_or_404(Tarefas, pk=task_id, responsavel=request.user)
            tarefa._user = request.user
            tarefa.status = new_status
            tarefa.save()
            return JsonResponse({'success': True, 'message': 'Status atualizado com sucesso.'})
        except Tarefas.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Tarefa não encontrada ou sem permissão.'}, status=404)
        except Exception as e:
            logger.error(f"Erro ao atualizar status da tarefa {task_id}: {e}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Requisição inválida.'}, status=400)

class RelatorioTarefasView(LoginRequiredMixin, View):
    # Usaremos um único template para a página de relatórios
    template_name = 'tarefas/relatorio_tarefas.html'

    def get(self, request, *args, **kwargs):
        """
        Busca os dados, prepara para JSON de forma limpa e renderiza o template.
        """
        # 1. Filtra os dados como antes
        queryset = Tarefas.objects.all().order_by('-data_criacao')
        status_filter = request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 2. Chama a função de serviço que já sabemos que está funcionando
        context = preparar_contexto_relatorio(queryset)

        # 3. Serializa os dados para os gráficos.
        #    Pega os dados diretamente do contexto retornado pelo serviço.
        #    Não há chance de erro aqui.
        status_data_list = context.get('status_data', [])
        priority_data_list = context.get('prioridade_data', [])

        # Pré-processa 'avg_duration' que é um objeto timedelta
        for item in status_data_list:
            avg_duration = item.get('avg_duration')
            if isinstance(avg_duration, timedelta):
                days = avg_duration.days
                hours, remainder = divmod(avg_duration.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                if days > 0:
                    item['avg_duration'] = f"{days}d {hours}h {minutes}m"
                else:
                    item['avg_duration'] = f"{hours}h {minutes}m"
            else:
                item['avg_duration'] = None
        
        # Adiciona as strings JSON ao contexto final
        context['status_data_json'] = json.dumps(status_data_list)
        context['priority_data_json'] = json.dumps(priority_data_list)
        
        # Adiciona o resto do contexto
        context['status_choices'] = Tarefas.STATUS_CHOICES
        context['current_filters'] = request.GET
        
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Este método lida APENAS com as solicitações de EXPORTAÇÃO.
        NENHUMA ALTERAÇÃO É NECESSÁRIA AQUI.
        """
        # Pega os filtros do formulário enviado
        status_filter = request.POST.get('status', '')
        export_format = request.POST.get('export_format')
        
        # Filtra os dados novamente com base nos dados do POST
        queryset = Tarefas.objects.all().order_by('-data_criacao')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Prepara o contexto para a exportação (usando os dados Python puros)
        context = preparar_contexto_relatorio(queryset)
        context['request'] = request
        
        # Chama a função de exportação correta
        if export_format == 'pdf':
            return gerar_pdf_relatorio(context)
            
        elif export_format == 'csv':
            return gerar_csv_relatorio(context)
            
        elif export_format == 'docx':
            return gerar_docx_relatorio(context)
            
        
        # Se nenhum formato de exportação for válido, volta para a página
        return redirect('tarefas:relatorio_tarefas')

class DashboardAnaliticoView(LoginRequiredMixin, TemplateView):
    template_name = 'tarefas/dashboard_analitico.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # --- 1. FILTROS E PERÍODO DE ANÁLISE ---
        hoje = timezone.now()
        trinta_dias_atras = hoje - timedelta(days=30)
        
        # --- 2. QUERIES ANALÍTICAS ---
        
        # A. Performance da Equipe (Tarefas Ativas e Concluídas por Responsável)
        concluidas_30d = Tarefas.objects.filter(
            responsavel=OuterRef('pk'),
            status='concluida',
            concluida_em__gte=trinta_dias_atras
        ).values('responsavel').annotate(c=Count('pk')).values('c')

        ativas = Tarefas.objects.filter(
            responsavel=OuterRef('pk')
        ).exclude(status__in=['concluida', 'cancelada']).values('responsavel').annotate(c=Count('pk')).values('c')

        usuarios = User.objects.filter(
            Q(tarefas_responsavel__isnull=False)
        ).distinct().annotate(
            tarefas_concluidas_30d=Subquery(concluidas_30d, output_field=models.IntegerField()),
            tarefas_ativas=Subquery(ativas, output_field=models.IntegerField()),
        ).order_by('-tarefas_ativas')
        
        # B. Tendência Semanal (Criadas vs. Concluídas)
        criadas_por_semana = Tarefas.objects.annotate(
            semana=TruncWeek('data_criacao')
        ).values('semana').annotate(total=Count('id')).order_by('semana')
        
        concluidas_por_semana = Tarefas.objects.filter(concluida_em__isnull=False).annotate(
            semana=TruncWeek('concluida_em')
        ).values('semana').annotate(total=Count('id')).order_by('semana')

        # C. Distribuição por Status e Prioridade
        status_dist = list(Tarefas.objects.values('status').annotate(total=Count('id')))
        prioridade_dist = list(Tarefas.objects.values('prioridade').annotate(total=Count('id')))

        # --- 3. PREPARAÇÃO DO CONTEXTO ---
        context['usuarios_performance'] = usuarios
        
        context['charts_data_json'] = json.dumps({
            'criadas_semana': list(criadas_por_semana),
            'concluidas_semana': list(concluidas_por_semana),
            'status_dist': status_dist,
            'prioridade_dist': prioridade_dist,
            'performance_equipe': [
                {'username': u.username, 'ativas': u.tarefas_ativas or 0, 'concluidas': u.tarefas_concluidas_30d or 0}
                for u in usuarios
            ]
        }, default=str) # default=str lida com datas/datetimes
        
        return context
    
@login_required
def update_task_status(request):
    if request.method == 'POST' and request.is_ajax():
        task_id = request.POST.get('task_id')
        new_status = request.POST.get('new_status')
        
        try:
            tarefa = Tarefas.objects.get(pk=task_id, responsavel=request.user)
            
            # Anexa o usuário que está fazendo a alteração para usar no método save()
            tarefa._user = request.user 
            
            tarefa.status = new_status
            tarefa.save()
            
            return JsonResponse({'success': True, 'message': 'Status atualizado com sucesso.'})
        except Tarefas.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Tarefa não encontrada ou você não tem permissão.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Requisição inválida.'}, status=400)


