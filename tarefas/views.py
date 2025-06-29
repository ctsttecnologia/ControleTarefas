
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
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import UpdateView
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.dateparse import parse_date
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import View, TemplateView, ListView
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
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

@login_required
def tarefas(request):
    """Lista todas as tarefas (para admin ou superusuário)"""
    if not request.user.is_superuser:
        return redirect('tarefas:listar_tarefas')
    
    tarefas = Tarefas.objects.all().order_by('-data_criacao')
    return render(request, 'tarefas/tarefas.html', {'tarefas': tarefas})

"""Cria uma nova tarefa"""
class TarefaCreateView(LoginRequiredMixin, CreateView):
    model = Tarefas
    form_class = TarefaForm
    template_name = 'tarefas/criar_tarefa.html' # Renomeei seu template para seguir a convenção
    success_url = reverse_lazy('tarefas:listar_tarefas') # Redireciona para a lista após sucesso

    def get_form_kwargs(self):
        """
      
        Envia o objeto 'request' para dentro do TarefaForm.
        """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """
        Esta função é chamada quando o formulário é válido.
        Aqui, adicionamos a mensagem de sucesso.
        """
        messages.success(self.request, "Tarefa criada com sucesso!")
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Esta função é chamada quando o formulário é inválido.
        Adicionamos uma mensagem de erro genérica para o usuário.
        """
        messages.error(self.request, "Por favor, corrija os erros no formulário.")
        return super().form_invalid(form)

"""Edita uma tarefa existente"""
@login_required
def editar_tarefa(request, pk):
    tarefa = get_object_or_404(Tarefas, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        form = TarefaForm(request.POST, instance=tarefa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tarefa atualizada com sucesso!')
            return redirect('tarefas:tarefa_detail', pk=pk)
        else:
            messages.error(request, 'Não foi possível salvar. Por favor, corrija os erros abaixo.')
    else:
        # Passando 'request' também no GET para qualquer lógica no __init__ que precise dele
        form = TarefaForm(instance=tarefa, request=request)
    
    context = {
        'form': form,
        'tarefa': tarefa
    }
    return render(request, 'tarefas/editar_tarefa.html', context) # ou o nome do seu template

@login_required
def excluir_tarefa(request, pk):
    """View para excluir uma tarefa com confirmação"""
    tarefa = get_object_or_404(Tarefas, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        try:
            tarefa.delete()
            logger.info(f'Tarefa {pk} excluída por {request.user}')
            messages.success(request, 'Tarefa excluída com sucesso!')
            return redirect('tarefas:listar_tarefas')
        except Exception as e:
            logger.error(f'Erro ao excluir tarefa {pk}: {str(e)}')
            messages.error(request, 'Erro ao excluir tarefa!')
            return redirect('tarefas:tarefa_detail', pk=pk)
    
    # Se for GET, mostrar página de confirmação
    return render(request, 'tarefas/confirmar_exclusao.html', {'tarefa': tarefa})

@login_required  # Garante que apenas usuários logados acessem o perfil
def profile_view(request):
    return render(request, 'usuario/profile.html')  # Renderiza o template do perfil

@login_required
def listar_tarefas(request):
    # Obter as choices diretamente do modelo
    status_choices = Tarefas.STATUS_CHOICES
    prioridade_choices = Tarefas.PRIORIDADE_CHOICES
    
    # Restante da lógica da view...
    tarefas = Tarefas.objects.all()
    
    return render(request, 'tarefas/listar_tarefas.html', {
        'tarefas': tarefas,
        'status_choices': status_choices,
        'prioridade_choices': prioridade_choices,
        # outros contextos...
    })

@login_required
def tarefa_detail(request, pk):
    """Detalhes de uma tarefa específica"""
    tarefa = get_object_or_404(Tarefas, pk=pk, usuario=request.user)
    comentarios = tarefa.comentarios.all().order_by('-criado_em')
    
    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.tarefa = tarefa
            comentario.autor = request.user
            comentario.save()
            messages.success(request, 'Comentário adicionado!')
            return redirect('tarefas:tarefa_detail', pk=pk)
    else:
        form = ComentarioForm()

    return render(request, 'tarefas/tarefa_detail.html', {
        'tarefa': tarefa,
        'form': form,
        'comentarios': comentarios,
    })

class TarefaUpdateView(UserPassesTestMixin, UpdateView):
    model = Tarefas
    form_class = TarefaForm
    
    def test_func(self):
        return self.get_object().usuario == self.request.user
    
@login_required
@require_POST
def atualizar_status(request, pk):
    tarefa = get_object_or_404(Tarefas, pk=pk, usuario=request.user)  # Adicionada verificação de usuário
    novo_status = request.POST.get('status')
    
    if novo_status and novo_status != tarefa.status:
        # Registrar histórico antes de atualizar
        HistoricoStatus.objects.create(
            tarefa=tarefa,
            status_anterior=tarefa.status,
            novo_status=novo_status,
            alterado_por=request.user
        )
        
        # Atualizar status
        tarefa.status = novo_status
        tarefa.save()
        
        messages.success(request, f'Status da tarefa atualizado para {tarefa.get_status_display()}')
    
    return redirect('tarefas:tarefa_detail', pk=pk)

"""
def criar_tarefa(request):
    if request.method == 'POST':
        # Aqui você extrairia os dados do POST (exemplo simplificado):
        titulo = request.POST.get('titulo')
        responsavel = request.POST.get('responsavel')  # Supondo que seja o ID

        tarefa = Tarefas.objects.create(
            titulo=titulo,
            responsavel_id=responsavel,
            # outros campos...
        )

        if tarefa.responsavel and tarefa.responsavel.email:
            send_mail(
                subject='Nova tarefa criada',
                message=f'Você foi designado para a tarefa: {tarefa.titulo}',
                from_email='esg.emerson@gmail.com',
                recipient_list=[tarefa.responsavel.email],
                fail_silently=False,
            )

        return redirect('lista_tarefas')
"""
@login_required
def calendario_tarefas(request):
    # Vamos buscar apenas tarefas que tenham um prazo definido
    tarefas = Tarefas.objects.filter(responsavel=request.user, prazo__isnull=False)
    eventos = []
    
    for tarefa in tarefas:
        eventos.append({
            'title': tarefa.titulo,
            'start': tarefa.prazo.isoformat(),
            'url': reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk}),
            
            # MUDANÇA: Em vez de 'color', usamos 'className' para o CSS estilizar
            'className': f'fc-event-prioridade-{tarefa.prioridade}'
        })
    
    return render(request, 'tarefas/calendario.html', {
        'eventos_json': json.dumps(eventos) # Passamos como JSON para ser mais seguro
    })

class RelatorioTarefasView(LoginRequiredMixin, View):
    # Usaremos um único template para a página de relatórios
    template_name = 'tarefas/relatorio_tarefas.html'

    def get(self, request, *args, **kwargs):
        """
        Este método agora busca os dados e exibe na tela, 
        seja na primeira visita ou ao aplicar filtros via GET.
        """
        # Filtra os dados com base nos parâmetros da URL (ex: ?status=pendente)
        queryset = Tarefas.objects.all().order_by('-data_criacao')
        status_filter = request.GET.get('status', '')

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Prepara todo o contexto para o template
        context = preparar_contexto_relatorio(queryset)
        context['status_choices'] = Tarefas.STATUS_CHOICES
        context['current_filters'] = request.GET # Para manter os filtros selecionados
        
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Este método lida APENAS com as solicitações de EXPORTAÇÃO.
        """
        # Pega os filtros do formulário enviado
        status_filter = request.POST.get('status', '')
        export_format = request.POST.get('export_format')
        
        # Filtra os dados novamente com base nos dados do POST
        queryset = Tarefas.objects.all().order_by('-data_criacao')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Prepara o contexto para a exportação
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

# tarefas/views.py
class KanbanView(LoginRequiredMixin, TemplateView):
    template_name = 'tarefas/kanban_board.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Status que aparecerão como colunas no quadro
        status_colunas_visiveis = ['pendente', 'andamento', 'pausada', 'atrasada']
        
        # Status que consideramos "ativos" para busca inicial
        status_ativos = ['pendente', 'andamento', 'pausada', 'atrasada']

        # Busca todas as tarefas que não estão finalizadas
        tarefas = Tarefas.objects.filter(
            responsavel=self.request.user,
        ).exclude(status__in=['concluida', 'cancelada']).select_related('responsavel')
        
        # >>> INÍCIO DA NOVA LÓGICA INTELIGENTE <<<
        tarefas_por_status = defaultdict(list)
        now = timezone.now()

        for tarefa in tarefas:
            # Verifica se a tarefa está de fato atrasada, independentemente do status salvo
            if tarefa.prazo and tarefa.prazo < now:
                # Se estiver atrasada, força a entrada na coluna "Atrasada"
                tarefas_por_status['atrasada'].append(tarefa)
            elif tarefa.status in status_ativos:
                # Se não estiver atrasada, usa o status salvo
                tarefas_por_status[tarefa.status].append(tarefa)
        # >>> FIM DA NOVA LÓGICA <<<

        # Prepara a lista de colunas na ordem correta para o template
        context['colunas'] = [
            {
                'id': status, 
                'nome': dict(Tarefas.STATUS_CHOICES)[status], 
                'tarefas': sorted(tarefas_por_status.get(status, []), key=lambda t: t.prazo or now) # Ordena por prazo
            }
            for status in status_colunas_visiveis
        ]
        
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


