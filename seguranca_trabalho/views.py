# seguranca_trabalho/views.py
from turtle import pd
from django.forms import DurationField
from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import render
from django.conf import settings
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404, HttpResponseForbidden
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.db.models.expressions import RawSQL
from django.contrib.staticfiles import finders
from django.db.models.functions import TruncMonth, Coalesce, Cast
from django.db.models.deletion import ProtectedError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Case, When, Value, F, ExpressionWrapper
from django.db.models.functions import Least, Cast
from django.db.models import DateField, Func, DurationField

from io import BytesIO
from datetime import timedelta, date
from .models import (Equipamento, FichaEPI, EntregaEPI, Fabricante, Fornecedor, Funcao, MatrizEPI, MovimentacaoEstoque)
from .forms import (EquipamentoForm, FichaEPIForm, EntregaEPIForm, AssinaturaForm, FabricanteForm, FornecedorForm)
from departamento_pessoal.models import Funcionario
from xhtml2pdf import pisa
from collections import defaultdict
from plotly.subplots import make_subplots

import plotly.graph_objects as go
import plotly.offline as opy
import plotly.express as px
import pandas as pd




# --- MIXINS E CLASSES BASE ---
class SSTPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Mixin para verificar se o usuário tem permissão para acessar a área de SST.
    Altere a permissão para uma mais específica do seu app.
    """
    permission_required = 'auth.view_user'  # Ex: 'seguranca_trabalho.view_equipamento'

    def handle_no_permission(self):
        messages.error(
            self.request, "Você não tem permissão para acessar esta página.")
        # Redireciona para o dashboard ou uma página de acesso negado
        return redirect(reverse_lazy('core:dashboard'))


class PaginationMixin:
    """Adiciona paginação a uma ListView."""
    paginate_by = 15


class SuccessDeleteMessageMixin:
    """Adiciona uma mensagem de sucesso ao deletar um objeto."""
    success_message = "Registro excluído com sucesso."

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)
    
class ControleEPIPorFuncaoView(LoginRequiredMixin, TemplateView):
    """
    Exibe e processa a matriz de EPIs por Função, permitindo
    definir a frequência de troca para cada combinação.
    """
    template_name = 'seguranca_trabalho/controle_epi_por_funcao.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        funcoes = Funcao.objects.filter(ativo=True).order_by('nome')
        equipamentos = Equipamento.objects.filter(ativo=True).order_by('nome')
        
        # Estrutura os dados existentes num dicionário aninhado para acesso eficiente no template.
        matriz_existente = MatrizEPI.objects.all()
        matriz_data = defaultdict(dict)
        for item in matriz_existente:
            matriz_data[item.funcao_id][item.equipamento_id] = item.frequencia_troca_meses
        
        context['funcoes'] = funcoes
        context['equipamentos'] = equipamentos
        context['matriz_data'] = matriz_data
        context['titulo_pagina'] = "Controle de EPI por Função"
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        Processa o formulário de forma otimizada, minimizando as consultas à base de dados.
        """
        # 1. Busca todos os registos existentes e organiza-os para consulta rápida.
        matriz_existente = {
            (item.funcao_id, item.equipamento_id): item
            for item in MatrizEPI.objects.all()
        }
        
        # 2. Prepara listas para as operações em massa (bulk operations).
        entradas_para_criar = []
        entradas_para_atualizar = []
        pks_para_apagar = []

        # 3. Itera sobre os dados enviados no formulário.
        for key, value in request.POST.items():
            if key.startswith('freq_'):
                try:
                    # Extrai os IDs da chave do input (ex: 'freq_1_15')
                    _, funcao_id_str, equipamento_id_str = key.split('_')
                    funcao_id = int(funcao_id_str)
                    equipamento_id = int(equipamento_id_str)
                    
                    # Converte o valor para inteiro, ou None se estiver vazio.
                    frequencia = int(value) if value else None
                    
                    chave = (funcao_id, equipamento_id)
                    item_existente = matriz_existente.get(chave)

                    # Se a frequência for nula ou zero, o registo deve ser apagado.
                    if not frequencia or frequencia <= 0:
                        if item_existente:
                            pks_para_apagar.append(item_existente.pk)
                    
                    # Se a frequência for um número positivo...
                    else:
                        # ...e o registo já existe, verifica se o valor mudou para o atualizar.
                        if item_existente:
                            if item_existente.frequencia_troca_meses != frequencia:
                                item_existente.frequencia_troca_meses = frequencia
                                entradas_para_atualizar.append(item_existente)
                        # ...e o registo não existe, prepara-o para ser criado.
                        else:
                            entradas_para_criar.append(
                                MatrizEPI(
                                    funcao_id=funcao_id,
                                    equipamento_id=equipamento_id,
                                    frequencia_troca_meses=frequencia
                                )
                            )
                except (ValueError, TypeError):
                    # Ignora chaves ou valores mal formatados, garantindo a robustez.
                    continue
        
        # 4. Executa as operações na base de dados de forma otimizada.
        if pks_para_apagar:
            MatrizEPI.objects.filter(pk__in=pks_para_apagar).delete()
        
        if entradas_para_atualizar:
            MatrizEPI.objects.bulk_update(entradas_para_atualizar, ['frequencia_troca_meses'])
            
        if entradas_para_criar:
            MatrizEPI.objects.bulk_create(entradas_para_criar)

        messages.success(request, "Matriz de EPIs atualizada com sucesso!")
        return redirect('seguranca_trabalho:controle_epi_por_funcao')


# --- VIEWS DO DASHBOARD ---
# IMPLEMENTADO: Adicionado o LoginRequiredMixin à classe da view.
# A ordem é importante: o mixin deve vir antes da classe base (TemplateView).
class DashboardSSTView(LoginRequiredMixin, TemplateView):
    template_name = 'seguranca_trabalho/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # --- KPIs ---
        context['total_equipamentos_ativos'] = Equipamento.objects.filter(ativo=True).count()
        context['fichas_ativas'] = FichaEPI.objects.filter(funcionario__status='ATIVO').count()
        context['entregas_pendentes_assinatura'] = EntregaEPI.objects.filter(
            (Q(assinatura_recebimento__isnull=True) | Q(assinatura_recebimento='')),
            (Q(assinatura_imagem__isnull=True) | Q(assinatura_imagem='')),
            data_devolucao__isnull=True
        ).count()

        # --- DADOS PARA GRÁFICOS ---
        future_date = date(2099, 12, 31)

        # Consulta compatível com MySQL
        entregas_ativas = EntregaEPI.objects.filter(
            data_entrega__isnull=False, 
            data_devolucao__isnull=True
        ).annotate(
            vida_util_dias_cast=Cast(F('equipamento__vida_util_dias'), output_field=DurationField()),
            vencimento_vida_util=Case(
                When(
                    equipamento__vida_util_dias__isnull=False,
                    then=ExpressionWrapper(
                        F('data_entrega') + F('vida_util_dias_cast'),
                        output_field=DateField()
                    )
                ),
                default=Value(future_date),
                output_field=DateField()
            ),
            validade_ca_definida=Case(
                When(equipamento__data_validade_ca__isnull=False, 
                     then=F('equipamento__data_validade_ca')),
                default=Value(future_date),
                output_field=DateField()
            )
        ).annotate(
            vencimento_final=Least('vencimento_vida_util', 'validade_ca_definida')
        )
        
        # --- GRÁFICO DE RISCO (PIZZA MODERNA) ---
        trinta_dias_frente = today + timedelta(days=30)
        cento_e_oitenta_dias_frente = today + timedelta(days=180)
        
        risco_counts = entregas_ativas.aggregate(
            vencidos=Count('id', filter=Q(vencimento_final__lt=today)),
            vencendo_30d=Count('id', filter=Q(vencimento_final__gte=today, vencimento_final__lte=trinta_dias_frente)),
            vencendo_180d=Count('id', filter=Q(vencimento_final__gt=trinta_dias_frente, vencimento_final__lte=cento_e_oitenta_dias_frente)),
            validos=Count('id', filter=Q(vencimento_final__gt=cento_e_oitenta_dias_frente))
        )
        
        if sum(risco_counts.values()) > 0:
            fig_risco = px.pie(
                names=['Vencidos', 'Vencendo (30d)', 'Alerta (31-180d)', 'Válidos (>180d)'],
                values=[risco_counts['vencidos'], risco_counts['vencendo_30d'], 
                       risco_counts['vencendo_180d'], risco_counts['validos']],
                hole=0.4,
                color_discrete_sequence=['#FF5252', '#FFAB40', '#FFD600', '#4CAF50'],
                title='Status de Validade dos EPIs em Uso'
            )
            fig_risco.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                marker=dict(line=dict(color='#FFFFFF', width=1))
            )
            fig_risco.update_layout(
                uniformtext_minsize=12,
                uniformtext_mode='hide',
                margin=dict(t=40, b=20, l=20, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2)
            )
            context['grafico_status_html'] = opy.plot(fig_risco, auto_open=False, output_type='div')

        # --- GRÁFICO DE VENCIMENTOS (BARRAS HORIZONTAIS) ---
        vencimentos_por_equipamento = entregas_ativas.filter(
            vencimento_final__gte=today, 
            vencimento_final__lte=cento_e_oitenta_dias_frente
        ).values('equipamento__nome').annotate(total=Count('id')).order_by('-total')[:10]

        if vencimentos_por_equipamento:
            df_vencimentos = pd.DataFrame(list(vencimentos_por_equipamento))
            fig_vencimentos = px.bar(
                df_vencimentos,
                y='equipamento__nome',
                x='total',
                orientation='h',
                text='total',
                title='Top 10 EPIs com Vencimentos Próximos (6 meses)',
                color='total',
                color_continuous_scale='OrRd'
            )
            fig_vencimentos.update_traces(
                textposition='outside',
                marker_line_color='rgba(0,0,0,0.2)',
                marker_line_width=1
            )
            fig_vencimentos.update_layout(
                xaxis_title="Quantidade",
                yaxis_title="Tipo de EPI",
                margin=dict(t=40, b=20, l=20, r=20),
                coloraxis_showscale=False,
                height=400
            )
            context['grafico_vencimentos_html'] = opy.plot(fig_vencimentos, auto_open=False, output_type='div')

        # --- GRÁFICO DE EPI POR FUNÇÃO (BARRAS HORIZONTAIS) ---
        funcoes_por_epi = MatrizEPI.objects.filter(
            funcao__ativo=True
        ).values('funcao__nome').annotate(total_epis=Count('equipamento')).order_by('-total_epis')[:10]

        if funcoes_por_epi:
            df_funcoes = pd.DataFrame(list(funcoes_por_epi))
            fig_funcao_epi = px.bar(
                df_funcoes,
                y='funcao__nome',
                x='total_epis',
                orientation='h',
                text='total_epis',
                title='Top 10 Funções por Quantidade de EPIs',
                color='total_epis',
                color_continuous_scale='Blues'
            )
            fig_funcao_epi.update_traces(
                textposition='outside',
                marker_line_color='rgba(0,0,0,0.2)',
                marker_line_width=1
            )
            fig_funcao_epi.update_layout(
                xaxis_title="Nº de Tipos de EPIs",
                yaxis_title="Função",
                margin=dict(t=40, b=20, l=20, r=20),
                coloraxis_showscale=False,
                height=400
            )
            context['grafico_funcao_epi_html'] = opy.plot(fig_funcao_epi, auto_open=False, output_type='div')

        return context

class RelatorioSSTPDFView(LoginRequiredMixin, TemplateView):
    template_name = 'seguranca_trabalho/relatorio_pdf_template.html'

    def get(self, request, *args, **kwargs):
        # Reutiliza a lógica da DashboardSSTView para obter todos os dados
        dashboard_view = DashboardSSTView()
        dashboard_view.request = request
        context = dashboard_view.get_context_data()

        # Opcional: Converter gráficos Plotly em imagens para o PDF
        # Esta é uma tarefa avançada que requer a biblioteca 'kaleido' (pip install kaleido)
        # fig_status = go.Figure(context['grafico_status_html'])
        # fig_status.write_image("static/graficos/status.png")
        # context['grafico_status_imagem_path'] = finders.find('graficos/status.png')

        template = get_template(self.template_name)
        html = template.render(context)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        if not pdf.err:
            return HttpResponse(result.getvalue(), content_type='application/pdf')
        return HttpResponse("Erro ao gerar PDF", status=400)

# --- CRUDs DE CATÁLOGO (Equipamento, Fabricante, Fornecedor) ---
# Fabricante
class FabricanteListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = Fabricante
    template_name = 'seguranca_trabalho/fabricante_list.html'


class FabricanteDetailView(SSTPermissionMixin, DetailView):
    model = Fabricante
    template_name = 'seguranca_trabalho/fabricante_detail.html'


class FabricanteCreateView(SSTPermissionMixin, SuccessMessageMixin, CreateView):
    model = Fabricante
    form_class = FabricanteForm
    template_name = 'seguranca_trabalho/fabricante_form.html'
    success_message = "Fabricante cadastrado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')


class FabricanteUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Fabricante
    form_class = FabricanteForm
    template_name = 'seguranca_trabalho/fabricante_form.html'
    success_message = "Fabricante atualizado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')


class FabricanteDeleteView(SSTPermissionMixin, SuccessDeleteMessageMixin, DeleteView):
    model = Fabricante
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')
    success_message = "Fabricante excluído com sucesso."

# Fornecedor
class FornecedorListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = Fornecedor
    template_name = 'seguranca_trabalho/ornecedor_list.html'


class FornecedorDetailView(SSTPermissionMixin, DetailView):
    model = Fornecedor
    template_name = 'seguranca_trabalho/fornecedor_detail.html'


class FornecedorCreateView(SSTPermissionMixin, SuccessMessageMixin, CreateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'seguranca_trabalho/fornecedor_form.html'
    success_message = "Fornecedor cadastrado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')


class FornecedorUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'seguranca_trabalho/fornecedor_form.html'
    success_message = "Fornecedor atualizado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')

# Equipamento
class EquipamentoListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = Equipamento
    queryset = Equipamento.objects.select_related(
        'fabricante').filter(ativo=True)
    template_name = 'seguranca_trabalho/equipamento_list.html'
    context_object_name = 'equipamentos'

    def get_context_data(self, **kwargs):
        # Primeiro, chama a implementação base para pegar o contexto existente
        context = super().get_context_data(**kwargs)

        # Agora, adiciona a sua própria informação ao contexto
        # Aqui contamos TODOS os equipamentos, ignorando o filtro 'ativo=True'
        context['total_geral_equipamentos'] = Equipamento.objects.count()

        return context


class EquipamentoDetailView(SSTPermissionMixin, DetailView):
    model = Equipamento
    queryset = Equipamento.objects.select_related(
        'fabricante', 'fornecedor_padrao')
    template_name = 'seguranca_trabalho/equipamento_detail.html'


class EquipamentoCreateView(SSTPermissionMixin, SuccessMessageMixin, CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_message = "Equipamento cadastrado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')


class EquipamentoUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_message = "Equipamento atualizado com sucesso!"

    def get_success_url(self):
        return reverse('seguranca_trabalho:equipamento_detail', kwargs={'pk': self.object.pk})


class EquipamentoDeleteView(SSTPermissionMixin, SuccessDeleteMessageMixin, DeleteView):
    model = Equipamento
    # Um template genérico de confirmação
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    success_message = "Equipamento excluído com sucesso."


# --- CRUD DE FICHAS DE EPI E ENTREGAS ---
class FichaEPIListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_list.html'
    context_object_name = 'fichas'
    queryset = FichaEPI.objects.select_related(
        'funcionario__cargo').filter(funcionario__status='ATIVO')


class FichaEPICreateView(SSTPermissionMixin, CreateView):
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_create.html'

    def form_valid(self, form):
        try:
            # Garante que o usuário do request seja o criador (se houver campo)
            # form.instance.criado_por = self.request.user
            self.object = form.save()
            messages.success(
                self.request, f"Ficha de EPI para {self.object.funcionario.nome_completo} criada com sucesso!")
            return redirect(self.get_success_url())
        except IntegrityError:
            messages.error(
                self.request, "Este funcionário já possui uma ficha de EPI.")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})


class FichaEPIDetailView(SSTPermissionMixin, DetailView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_detail.html'
    context_object_name = 'ficha'

    def get_queryset(self):
        # Otimiza a query para buscar dados relacionados de uma só vez
        return FichaEPI.objects.select_related(
            'funcionario__cargo', 
            'funcao',
            'funcionario__cliente' # Busca o cliente (que contém o contrato) do funcionário
        ).prefetch_related(
            'entregas__equipamento'
        ).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entrega_form'] = EntregaEPIForm()
        context['assinatura_form'] = AssinaturaForm()
        return context
    
class FichaEPIUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = FichaEPI
    form_class = FichaEPIForm # Reutiliza o mesmo formulário da criação
    template_name = 'seguranca_trabalho/ficha_create.html' # Reutiliza o template
    success_message = "Ficha de EPI atualizada com sucesso!"

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})


class FichaEPIDeleteView(DeleteView): # Se você usa um Mixin de permissão, adicione-o aqui também
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_delete.html'  # Certifique-se que este template existe
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')  # Mude 'ficha_list' para o nome da sua URL da lista de fichas

    def post(self, request, *args, **kwargs):
        """
        Sobrescreve o método post para tratar o ProtectedError.
        """
        self.object = self.get_object()
        try:
            # Tenta deletar o objeto normalmente
            response = self.object.delete()
            messages.success(request, f"A Ficha de EPI para '{self.object.funcionario}' foi excluída com sucesso.")
            return redirect(self.success_url)

        except ProtectedError:
            # Se a exclusão for bloqueada, entra aqui
            messages.error(
                request, 
                "Exclusão não permitida. Esta ficha possui um histórico de entregas de EPIs associado. Por favor, contate o administrador do sistema."
            )
            # Redireciona de volta para a página de detalhes da ficha que falhou em ser excluída
            return redirect('seguranca_trabalho:ficha_detail', pk=self.object.pk) # Mude 'ficha_detail' para o nome da sua URL de detalhes


# --- VIEWS DE AÇÃO (Entregas, Assinaturas, Devoluções) ---
class AdicionarEntregaView(SSTPermissionMixin, View):
    """
    Processa o formulário para adicionar um novo EPI a uma Ficha.
    """
    @transaction.atomic # Garante que a entrega e a movimentação de estoque ocorram juntas
    def post(self, request, *args, **kwargs):
        ficha = get_object_or_404(FichaEPI, pk=kwargs.get('ficha_pk'))
        form = EntregaEPIForm(request.POST)

        if form.is_valid():
            entrega = form.save(commit=False)
            entrega.ficha = ficha
            entrega.save()

            # Lógica para abater do estoque, se aplicável
            MovimentacaoEstoque.objects.create(
                equipamento=entrega.equipamento,
                tipo='SAIDA',
                quantidade=-entrega.quantidade, # Negativo para indicar saída
                responsavel=request.user,
                justificativa=f"Entrega para {ficha.funcionario.nome_completo}",
                entrega_associada=entrega
            )

            messages.success(request, f"Entrega de '{entrega.equipamento.nome}' registrada. Aguardando assinatura do colaborador.")
        else:
            # Concatena os erros do formulário em uma única mensagem
            error_list = [f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()]
            error_message = "Erro ao registrar entrega. " + " ".join(error_list)
            messages.error(request, error_message)

        return redirect('seguranca_trabalho:ficha_detail', pk=ficha.pk)


class AssinarEntregaView(SSTPermissionMixin, View):
    def post(self, request, *args, **kwargs):
        pk_da_entrega = kwargs.get('pk')
        entrega = get_object_or_404(EntregaEPI, pk=pk_da_entrega)

        # --- LÓGICA ATUALIZADA ---
        # Prioriza o upload de arquivo se ele existir
        if request.FILES.get('assinatura_imagem'):
            entrega.assinatura_imagem = request.FILES['assinatura_imagem']
            # Limpa o campo de assinatura base64, se houver, para evitar duplicidade
            entrega.assinatura_recebimento = None
            messages.success(request, "Assinatura anexada com sucesso!")
        
        # Se não houver arquivo, procura pela assinatura desenhada
        elif request.POST.get('assinatura_base64'):
            form = AssinaturaForm(request.POST)
            if form.is_valid():
                entrega.assinatura_recebimento = form.cleaned_data['assinatura_base64']
                # Limpa o campo de imagem, se houver
                entrega.assinatura_imagem = None
                messages.success(request, "Assinatura desenhada salva com sucesso!")
            else:
                messages.error(request, "Erro no formulário de assinatura desenhada.")
                return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)
        
        else:
             messages.error(request, "Nenhuma assinatura foi fornecida (desenhada ou anexada).")
             return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)

        # Salva as alterações para ambos os casos
        entrega.data_entrega = timezone.now()
        entrega.save()

        return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)


class RegistrarDevolucaoView(SSTPermissionMixin, View):
    """
    Registra a data da devolução de um EPI.
    """
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        entrega = get_object_or_404(EntregaEPI, pk=kwargs.get('pk'), data_devolucao__isnull=True)

        entrega.data_devolucao = timezone.now()
        entrega.recebedor_devolucao = request.user
        entrega.save(update_fields=['data_devolucao', 'recebedor_devolucao'])

        # Opcional: Lógica para retornar o item ao estoque, se for reutilizável
        # MovimentacaoEstoque.objects.create(...)

        messages.success(request, "Devolução de EPI registrada com sucesso!")
        return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)


# Gerador de relatório PDF
class GerarFichaPDFView(SSTPermissionMixin, DetailView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_pdf_template.html'

    def render_to_pdf(self, template_src, context_dict={}):
        template = get_template(template_src)
        html = template.render(context_dict)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        if not pdf.err:
            return HttpResponse(result.getvalue(), content_type='application/pdf')
        return None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        
        # Otimiza a query para buscar todos os dados necessários para o PDF
        context['ficha'] = FichaEPI.objects.select_related(
            'funcionario__cargo', 'funcao'
        ).prefetch_related(
            'entregas__equipamento'
        ).get(pk=self.object.pk)

        # Encontra o caminho absoluto da logomarca nos arquivos estáticos
        logo_path = finders.find('seguranca_trabalho/images/logocetest.png')
        
        context['logo_path'] = logo_path

        pdf = self.render_to_pdf(self.template_name, context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            # Define o nome do arquivo para download
            filename = f"Ficha_EPI_{self.object.funcionario.nome_completo}.pdf"
            content = f"inline; filename='{filename}'"
            response['Content-Disposition'] = content
            return response
        return HttpResponse("Erro ao gerar PDF", status=400)
    

