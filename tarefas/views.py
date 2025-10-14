# tarefas/views.py
import json
import logging
from collections import defaultdict
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Count, OuterRef, Subquery, IntegerField
from django.db.models.functions import TruncWeek
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormMixin
from django.core.serializers.json import DjangoJSONEncoder
from requests import request
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .utils import enviar_email_tarefa 
from .models import Tarefas, Comentario, HistoricoStatus
from .forms import TarefaForm, ComentarioForm
from .services import preparar_contexto_relatorio, gerar_pdf_relatorio, gerar_csv_relatorio, gerar_docx_relatorio
from core.mixins import ViewFilialScopedMixin, TarefaPermissionMixin


User = get_user_model()
logger = logging.getLogger(__name__)
# =============================================================================
# == VIEWS DE GERENCIAMENTO (CRUD)
# =============================================================================
class TarefaListView(LoginRequiredMixin, ViewFilialScopedMixin, TarefaPermissionMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/listar_tarefas.html'
    context_object_name = 'object_list' # Usar object_list é o padrão e evita conflitos
    paginate_by = 20

    def get_queryset(self):
        # 1. Obtém o queryset inicial já filtrado pela filial
        queryset = super().get_queryset()

        # 2. Pega os valores dos filtros da URL (via GET)
        status_filtro = self.request.GET.get('status', '')
        prioridade_filtro = self.request.GET.get('prioridade', '')
        query_busca = self.request.GET.get('q', '')

        # 3. Aplica os filtros ao queryset
        if status_filtro:
            queryset = queryset.filter(status=status_filtro)
        
        if prioridade_filtro:
            queryset = queryset.filter(prioridade=prioridade_filtro)

        if query_busca:
            queryset = queryset.filter(
                Q(titulo__icontains=query_busca) |
                Q(descricao__icontains=query_busca) |
                Q(projeto__icontains=query_busca)
            )

        # 4. Otimiza e ordena o resultado final
        return queryset.select_related('usuario', 'responsavel', 'filial').order_by('-prazo', 'prioridade')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # --- LÓGICA DE CONTAGEM ---
        # Pega a lista de tarefas da filial ATUAL, SEM filtros, para os contadores
        base_qs = super().get_queryset()
        context['total_tarefas'] = base_qs.count()
        context['tarefas_concluidas'] = base_qs.filter(status='concluida').count()
        # Tarefas pendentes são todas que não estão concluídas ou canceladas
        context['tarefas_pendentes'] = base_qs.exclude(status__in=['concluida', 'cancelada']).count()

        # --- DADOS PARA OS DROPDOWNS DE FILTRO ---
        context['status_options'] = Tarefas.STATUS_CHOICES
        context['prioridade_options'] = Tarefas.PRIORIDADE_CHOICES
        
        # Mantém os valores selecionados nos filtros após o envio
        context['request'] = self.request 

        return context

class TarefaDetailView(LoginRequiredMixin, ViewFilialScopedMixin, TarefaPermissionMixin, FormMixin, DetailView):
    model = Tarefas
    template_name = 'tarefas/tarefa_detail.html'
    form_class = ComentarioForm

    def get_queryset(self):
        # Obtém o queryset inicial do mixin, passando o objeto request
        queryset = super().get_queryset() 
        
        # Agora aplica as otimizações adicionais
        return queryset.select_related('usuario', 'responsavel', 'filial')

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
    success_url = reverse_lazy('tarefas:kanban_board') 

    def get_form_kwargs(self):
        """
        Passa o objeto 'request' para o formulário.
        Isso é útil se o formulário precisar acessar dados da sessão ou do usuário.
        """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """
        Este método é chamado após a validação bem-sucedida do formulário.
        """
        # 1. Define os campos que não vêm do formulário antes de salvar.
        form.instance.usuario = self.request.user
        filial_id = self.request.session.get('active_filial_id')
        if filial_id:
            form.instance.filial_id = filial_id
        
        # 2. Deixa a classe pai (super) salvar o objeto e retornar a resposta de redirecionamento.
        #    Isso é mais limpo do que chamar form.save() e redirect() manualmente.
        response = super().form_valid(form)
        
        # 3. 'self.object' agora contém a tarefa recém-criada e salva.
        tarefa_criada = self.object

        # 4. (Opcional, mas recomendado) Envia e-mail de notificação para o responsável.
        if tarefa_criada.responsavel:
            enviar_email_tarefa(
                assunto=f"Nova tarefa atribuída a você: '{tarefa_criada.titulo}'",
                template_texto='tarefas/emails/email_nova_tarefa.txt',
                template_html='tarefas/emails/email_nova_tarefa.html',
                contexto={'tarefa': tarefa_criada, 'criador': self.request.user},
                destinatarios=[tarefa_criada.responsavel.email]
            )

        # 5. Adiciona a mensagem de sucesso.
        messages.success(self.request, "Tarefa criada com sucesso!")
        
        # 6. Retorna a resposta de redirecionamento criada pelo 'super()'.
        return response

class TarefaUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, TarefaPermissionMixin, UpdateView):
    model = Tarefas
    form_class = TarefaForm
    template_name = 'tarefas/editar_tarefa.html'
    context_object_name = 'tarefa'
    success_url = reverse_lazy('tarefas:listar_tarefas')

    def get_queryset(self):
        """
        Garante que o mixin de filial receba o request para filtrar corretamente.
        """
        return super().get_queryset()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """
        Este método é chamado quando o formulário é válido.
        """
        tarefa_antes_da_edicao = self.get_object()
        status_anterior = tarefa_antes_da_edicao.get_status_display()
        
        # Deixa a classe pai salvar o objeto primeiro
        response = super().form_valid(form)
        
        # 'self.object' agora contém a tarefa já atualizada
        tarefa_atualizada = self.object
        novo_status_display = tarefa_atualizada.get_status_display()

        # Verifica se o status realmente mudou para evitar e-mails desnecessários
        if status_anterior != novo_status_display:
            
            # --- PREPARA OS ARGUMENTOS PARA A FUNÇÃO DE E-MAIL ---
            
            # 1. Define o assunto
            assunto = f"Status da tarefa '{tarefa_atualizada.titulo}' foi alterado"
            
            # 2. Monta o dicionário de contexto para os templates
            contexto = {
                'tarefa': tarefa_atualizada,
                'status_anterior': status_anterior,
                'novo_status': novo_status_display,
                'alterado_por': self.request.user,
                'request': self.request,
            }
            
            # 3. Define a lista de destinatários (criador e responsável)
            destinatarios = set()
            if tarefa_atualizada.usuario and tarefa_atualizada.usuario.email:
                destinatarios.add(tarefa_atualizada.usuario.email)
            if tarefa_atualizada.responsavel and tarefa_atualizada.responsavel.email:
                destinatarios.add(tarefa_atualizada.responsavel.email)

            # 4. Chama a função utilitária com os argumentos CORRETOS
            if destinatarios:
                enviar_email_tarefa(
                    assunto=assunto,
                    template_texto='tarefas/emails/email_notificacao_status.txt',
                    template_html='tarefas/emails/email_notificacao_status.html',
                    contexto=contexto,
                    destinatarios=list(destinatarios)
                )

        messages.success(self.request, f"Tarefa '{tarefa_atualizada.titulo}' atualizada com sucesso!")
        return response

class ConcluirTarefaView(View):
    def get(self, request, pk):
        tarefa = get_object_or_404(Tarefas, pk=pk)
        
        # Lógica para marcar a tarefa como concluída
        if tarefa.status != 'concluida':
            tarefa.status = 'concluida'
            tarefa.save()
            messages.success(request, f'A tarefa "{tarefa.titulo}" foi marcada como concluída!')
        else:
            messages.info(request, 'Esta tarefa já estava concluída.')
            
        return redirect('tarefas:listar_tarefas')

class TarefaDeleteView(LoginRequiredMixin, ViewFilialScopedMixin, UserPassesTestMixin, DeleteView):
    model = Tarefas
    template_name = 'tarefas/confirmar_exclusao.html'
    success_url = reverse_lazy('tarefas:listar_tarefas')

    def get_queryset(self):
        """
        Garante que o mixin de filial receba o request para filtrar corretamente.
        """
        return super().get_queryset()

    def test_func(self):
        return self.request.user == self.get_object().usuario

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Tarefa excluída com sucesso!")
        return response

# =============================================================================
# == VIEWS DE VISUALIZAÇÃO (KANBAN, CALENDÁRIO)
# =============================================================================

class KanbanView(LoginRequiredMixin, ViewFilialScopedMixin, TarefaPermissionMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/kanban_board.html'
    context_object_name = 'tarefas' # Definir isso é uma boa prática em ListView

    def get_queryset(self):
        """Filtra apenas as tarefas ativas para o quadro Kanban."""
        # 1. Primeiro, obtenha o queryset já filtrado pela filial, passando o request.
        queryset = super().get_queryset()
        # 2. Em seguida, aplique o seu filtro de status específico para o Kanban.
        active_statuses = ['pendente', 'atrasada', 'andamento', 'concluida', 'pausada']
        return queryset.filter(status__in=active_statuses)

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
        colunas_ordenadas = ['pendente', 'atrasada', 'andamento', 'concluida', 'pausada']
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
        from_email='esg@cetestsp.com',
        to=[usuario.email]
    )
    email.attach_alternative(corpo_html, "text/html")
    email.send()

class CalendarioTarefasView(LoginRequiredMixin, ViewFilialScopedMixin, TarefaPermissionMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/calendario.html'

    def get_queryset(self):
        """
        Garante que o mixin de filial receba o request para filtrar corretamente.
        """   
        return super().get_queryset().filter(prazo__isnull=False).exclude(status__in=['cancelada'])

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

class RelatorioTarefasView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Tarefas
    template_name = 'tarefas/relatorio_tarefas.html'
    
    def get_queryset(self):
        # 1. Chame o super() CORRETAMENTE, passando o request para o mixin de filial.
        qs = super().get_queryset()

        # 2. Obtenha o valor do filtro de status.
        status_filter = self.request.GET.get('status') or self.request.POST.get('status')
        
        # 3. Aplique o filtro de status apenas se um valor foi fornecido.
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        # 4. Ordene o resultado final e retorne.
        return qs.order_by('-data_criacao')

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
    template_name = 'tarefas/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_filial_id = self.request.session.get('active_filial_id')

        # --- Querysets Base (já corrigidos) ---
        base_queryset = Tarefas.objects.all()
        if active_filial_id:
            base_queryset = base_queryset.filter(filial_id=active_filial_id)
        
        usuarios = User.objects.all()
        if active_filial_id:
            usuarios = usuarios.filter(filiais_permitidas__id=active_filial_id)

        # --- DADOS PARA A TABELA ---
        usuarios_performance = []
        thirty_days_ago = timezone.now() - timedelta(days=30)
        for usuario in usuarios:
            ativas = base_queryset.filter(responsavel=usuario, status__in=['pendente', 'andamento', 'atrasada']).count()
            concluidas = base_queryset.filter(responsavel=usuario, status='concluida', concluida_em__gte=thirty_days_ago).count()
            if ativas > 0 or concluidas > 0:
                usuarios_performance.append({
                    'username': usuario.username, 'tarefas_ativas': ativas, 'tarefas_concluidas_30d': concluidas
                })
        context['usuarios_performance'] = usuarios_performance
        
        # --- DADOS PARA OS GRÁFICOS ---
        charts_data = {}
        
        # =========================================================================
        # REFATORAÇÃO DO GRÁFICO DE TENDÊNCIA
        # =========================================================================

        # 1. Pega os dados brutos do banco de dados
        six_weeks_ago_dt = timezone.now() - timedelta(weeks=6)
        
        criadas_por_semana_qs = base_queryset.filter(data_criacao__gte=six_weeks_ago_dt)\
            .annotate(semana=TruncWeek('data_criacao'))\
            .values('semana')\
            .annotate(total=Count('id'))\
            .order_by('semana')

        concluidas_por_semana_qs = base_queryset.filter(concluida_em__gte=six_weeks_ago_dt, status='concluida')\
            .annotate(semana=TruncWeek('concluida_em'))\
            .values('semana')\
            .annotate(total=Count('id'))\
            .order_by('semana')
        
        # 2. Converte os dados brutos para dicionários para busca rápida
        dados_criadas = {item['semana'].date(): item['total'] for item in criadas_por_semana_qs}
        dados_concluidas = {item['semana'].date(): item['total'] for item in concluidas_por_semana_qs}

        # 3. Gera um intervalo completo de semanas (as últimas 6)
        hoje = timezone.now().date()
        semana_inicial = hoje - timedelta(weeks=5)
        
        labels_semanas = []
        dados_finais_criadas = []
        dados_finais_concluidas = []
        
        # Garante que a primeira semana comece no início da semana (ex: segunda-feira)
        current_week = semana_inicial - timedelta(days=semana_inicial.weekday())

        while current_week <= hoje:
            labels_semanas.append(current_week)
            dados_finais_criadas.append(dados_criadas.get(current_week, 0))
            dados_finais_concluidas.append(dados_concluidas.get(current_week, 0))
            current_week += timedelta(weeks=1)

        # 4. Adiciona os dados completos e formatados ao dicionário do gráfico
        charts_data['tendencia_labels'] = labels_semanas
        charts_data['tendencia_criadas'] = dados_finais_criadas
        charts_data['tendencia_concluidas'] = dados_finais_concluidas
        
        # --- Gráfico de Performance (sem alteração na lógica, apenas na passagem de dados) ---
        charts_data['performance_equipe'] = usuarios_performance

        # Converte para JSON
        context['charts_data_json'] = json.dumps(charts_data, cls=DjangoJSONEncoder)

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

