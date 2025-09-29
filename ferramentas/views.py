# ferramentas/views.py

import base64
import json
from datetime import timedelta, datetime
from io import BytesIO
import subprocess
import sys
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (CreateView, DetailView, FormView, ListView, TemplateView, UpdateView)
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from core.mixins import SSTPermissionMixin, ViewFilialScopedMixin, AtividadeLogMixin
from usuario.models import Filial
from .forms import (DevolucaoForm, FerramentaForm, MovimentacaoForm, UploadFileForm, MalaFerramentasForm, TermoResponsabilidadeForm) 
from .models import Atividade, Ferramenta, MalaFerramentas, Movimentacao, TermoDeResponsabilidade, ItemTermo
from django.db.models import Prefetch
from django.template.loader import render_to_string
from django.http import HttpResponse
import tempfile
import zipfile
import os

# =============================================================================
# == VIEWS PRINCIPAIS (ATUALIZADO)
# =============================================================================

# Adicionado ViewFilialScopedMixin para garantir que a view seja consistente
class DashboardView(LoginRequiredMixin, ViewFilialScopedMixin, TemplateView):
    """
    Exibe o dashboard principal com estatísticas sobre ferramentas e malas.
    O código é otimizado para minimizar as consultas ao banco de dados.
    """
    template_name = 'ferramentas/dashboard.html'

    def _get_ferramenta_stats(self, base_qs):
        """
        Calcula todas as estatísticas de ferramentas em uma única consulta.
        """
        # Define as condições de filtro para cada status
        em_uso_q = Q(status=Ferramenta.Status.EM_USO) | Q(mala__status=MalaFerramentas.Status.EM_USO)
        em_manutencao_q = Q(status=Ferramenta.Status.EM_MANUTENCAO)
        
        # Ferramentas disponíveis são aquelas que NÃO estão em uso E NÃO estão em manutenção
        disponivel_q = ~em_uso_q & ~em_manutencao_q

        # Executa uma única consulta de agregação para obter todos os dados
        stats = base_qs.aggregate(
            # Contagem de registros por status
            total_count=Count('id'),
            em_uso_count=Count('id', filter=em_uso_q),
            em_manutencao_count=Count('id', filter=em_manutencao_q),
            disponivel_count=Count('id', filter=disponivel_q),

            # Soma da quantidade de itens por status
            total_sum=Sum('quantidade'),
            em_uso_sum=Sum('quantidade', filter=em_uso_q),
            disponivel_sum=Sum('quantidade', filter=disponivel_q),
        )
        return stats

    def _get_mala_stats(self, base_qs):
        """
        Calcula todas as estatísticas de malas em uma única consulta.
        """
        # Define as condições de filtro
        disponivel_q = Q(status=MalaFerramentas.Status.DISPONIVEL)
        em_uso_q = Q(status=MalaFerramentas.Status.EM_USO)

        # Executa a agregação
        stats = base_qs.aggregate(
            # Contagem de registros
            total_count=Count('id'),
            disponivel_count=Count('id', filter=disponivel_q),
            em_uso_count=Count('id', filter=em_uso_q),

            # Soma da quantidade de itens
            total_sum=Sum('quantidade'),
            disponivel_sum=Sum('quantidade', filter=disponivel_q),
        )
        return stats

    def _prepare_context_data(self, context, ferramenta_stats, mala_stats, movimentacoes_qs, atividades_qs):
        """
        Popula o dicionário de contexto com os dados já calculados.
        Nenhuma consulta ao banco de dados é feita aqui.
        """
        context['status_malas'] = mala_stats
        # Combina os totais para os cards principais
        context['status_total'] = {
            'total': (ferramenta_stats.get('total_count') or 0) + (mala_stats.get('total_count') or 0),
            'disponivel': (ferramenta_stats.get('disponivel_count') or 0) + (mala_stats.get('disponivel_count') or 0),
            'em_uso': (ferramenta_stats.get('em_uso_count') or 0) + (mala_stats.get('em_uso_count') or 0),
            'em_manutencao': ferramenta_stats.get('em_manutencao_count') or 0,
            
            'total_itens_ferramentas': ferramenta_stats.get('total_sum') or 0,
            'total_itens_malas': mala_stats.get('total_sum') or 0,
            'total_itens_geral': (ferramenta_stats.get('total_sum') or 0) + (mala_stats.get('total_sum') or 0),
            
            'quantidade_ferramentas_disponiveis': (ferramenta_stats.get('disponivel_count') or 0),
            'quantidade_malas_disponiveis': (mala_stats.get('disponivel_count') or 0),

            'total_malas': mala_stats.get('total_count') or 0,
            'total_ferramentas': ferramenta_stats.get('total_count') or 0,
            'total_movimentacoes': movimentacoes_qs.count(), # .count() aqui é ok, pois é a última operação na queryset
            'total_atividades': atividades_qs.count(),
        }

        # Prepara dados para os gráficos Pizza
        context['ferramentas_chart_data'] = {
            'labels': ['Disponível', 'Em Uso', 'Em Manutenção'],
            'data': [
                ferramenta_stats.get('disponivel_count') or 0,
                ferramenta_stats.get('em_uso_count') or 0,
                ferramenta_stats.get('em_manutencao_count') or 0
            ],
            'title': 'Distribuição de Ferramentas'
        }
        
        context['malas_chart_data'] = {
            'labels': ['Disponível', 'Em Uso'],
            'data': [
                mala_stats.get('disponivel_count') or 0,
                mala_stats.get('em_uso_count') or 0
            ],
            'title': 'Distribuição de Malas/Kits'
        }

        # Prepara listas de itens em uso e atividades
        context['ferramentas_em_uso'] = movimentacoes_qs.filter(
            data_devolucao__isnull=True, ferramenta__isnull=False
        ).select_related('ferramenta', 'retirado_por')
        
        context['malas_em_uso'] = movimentacoes_qs.filter(
            data_devolucao__isnull=True, mala__isnull=False
        ).select_related('mala', 'retirado_por')
        
        context['ultimas_atividades'] = atividades_qs.order_by('-timestamp')[:10]
        context['titulo_pagina'] = "Dashboard de Operações"
        
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # 1. BUSCA AS QUERYSETS BASE
        malas_qs = MalaFerramentas.objects.for_request(request)
        movimentacoes_qs = Movimentacao.objects.for_request(request)
        atividades_qs = Atividade.objects.for_request(request)
        ferramentas_qs = Ferramenta.objects.for_request(request).exclude(status=Ferramenta.Status.DESCARTADA)

        # 2. CALCULA ESTATÍSTICAS (Acessa o banco de dados de forma otimizada)
        ferramenta_stats = self._get_ferramenta_stats(ferramentas_qs)
        mala_stats = self._get_mala_stats(malas_qs)

        # 3. MONTA O CONTEXTO FINAL (Sem novas consultas ao banco)
        context = self._prepare_context_data(context, ferramenta_stats, mala_stats, movimentacoes_qs, atividades_qs)

        return context
    
# =============================================================================
# == VIEWS DE FERRAMENTAS
# =============================================================================

class FerramentaListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Ferramenta
    template_name = 'ferramentas/ferramenta_list.html'
    context_object_name = 'ferramentas'
    paginate_by = 30
    # O queryset base é definido pelo ViewFilialScopedMixin
    # queryset = Ferramenta.objects.select_related('mala', 'filial').order_by('nome') # Removido para usar o mixin

    def get_queryset(self):
        # Chama o get_queryset do mixin primeiro
        queryset = super().get_queryset().select_related('mala', 'filial')
        search_query = self.request.GET.get('q')
        status_filter = self.request.GET.get('status')

        if search_query:
            queryset = queryset.filter(
                Q(nome__icontains=search_query) |
                Q(codigo_identificacao__icontains=search_query) |
                Q(patrimonio__icontains=search_query)
            )

        if status_filter:
            if status_filter == Ferramenta.Status.EM_USO:
                queryset = queryset.filter(Q(status=status_filter) | Q(mala__status=status_filter))
            elif status_filter == Ferramenta.Status.DISPONIVEL:
                queryset = queryset.filter(status=status_filter).filter(
                    Q(mala__isnull=True) | Q(mala__status=status_filter)
                )
            else:
                queryset = queryset.filter(status=status_filter)
        else:
            queryset = queryset.exclude(status=Ferramenta.Status.DESCARTADA)
            
        return queryset.distinct().order_by('nome')

class FerramentaDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Ferramenta
    template_name = 'ferramentas/ferramenta_detail.html'
    context_object_name = 'ferramenta'
    
    def get_queryset(self):
        # Adiciona prefetch_related ao queryset já filtrado pelo mixin
        return super().get_queryset().prefetch_related('movimentacoes__retirado_por', 'atividades__usuario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ferramenta = self.object
        
        context['status_efetivo'] = ferramenta.status_efetivo
        context['status_efetivo_display'] = dict(Ferramenta.Status.choices).get(ferramenta.status_efetivo)
        
        context['movimentacoes'] = ferramenta.movimentacoes.all()
        context['atividades'] = ferramenta.atividades.all()[:20]
        context['movimentacao_ativa'] = next((m for m in context['movimentacoes'] if m.esta_ativa), None)
        
        six_months_ago = timezone.now() - timedelta(days=180)
        usage_data = (
            Movimentacao.objects.filter(ferramenta=ferramenta, data_retirada__gte=six_months_ago)
            .annotate(month=TruncMonth('data_retirada')).values('month')
            .annotate(count=Count('id')).order_by('month')
        )
        context['chart_labels'] = json.dumps([d['month'].strftime('%b/%Y') for d in usage_data])
        context['chart_data'] = json.dumps([d['count'] for d in usage_data])
        context['titulo_pagina'] = f"Painel de Controle: {ferramenta.nome}"
        return context

# Adicionado ViewFilialScopedMixin por consistência, embora a lógica principal esteja no form_valid
class FerramentaCreateView(LoginRequiredMixin, ViewFilialScopedMixin, AtividadeLogMixin, CreateView):
    model = Ferramenta
    form_class = FerramentaForm
    template_name = 'ferramentas/ferramenta_form.html'

    def form_valid(self, form):
        # A lógica de atribuição da filial já está correta
        if self.request.user.is_superuser and self.request.session.get('active_filial_id'):
            form.instance.filial_id = self.request.session.get('active_filial_id')
        else:
            form.instance.filial = self.request.user.filial_ativa
        
        messages.success(self.request, "Ferramenta adicionada com sucesso.")
        response = super().form_valid(form) 
        self._log_atividade(
            ferramenta=self.object, 
            tipo=Atividade.TipoAtividade.CRIACAO, 
            descricao=f"Ferramenta '{self.object.nome}' registrada."
        )
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = "Adicionar Nova Ferramenta"
        return context

class FerramentaUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, AtividadeLogMixin, UpdateView):
    model = Ferramenta
    form_class = FerramentaForm
    template_name = 'ferramentas/ferramenta_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, "Dados da ferramenta atualizados com sucesso.")
        response = super().form_valid(form)
        self._log_atividade(
            ferramenta=self.object, 
            tipo=Atividade.TipoAtividade.ALTERACAO, 
            descricao="Dados da ferramenta foram atualizados."
        )
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar: {self.object.nome}"
        return context
    
# =============================================================================
# == NOVAS VIEWS PARA MALAS DE FERRAMENTAS
# =============================================================================

class MalaListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = MalaFerramentas
    template_name = 'ferramentas/mala_list.html'
    context_object_name = 'malas'
    paginate_by = 20

    def get_queryset(self):
        """
        Sobrescreve o queryset original para aplicar filtros de busca e anotações.
        """
        # Pega o queryset base já filtrado pelo mixin
        base_queryset = super().get_queryset()
        
        query = self.request.GET.get('q', '')

        if query:
            base_queryset = base_queryset.filter(
                Q(nome__icontains=query) |
                Q(codigo_identificacao__icontains=query)
            )

        return base_queryset.annotate(
            item_count=Count('itens')
        ).prefetch_related('itens').order_by('nome')

class MalaDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = MalaFerramentas
    template_name = 'ferramentas/mala_detail.html'
    context_object_name = 'mala'
    
    def get_queryset(self):
        return super().get_queryset().prefetch_related('movimentacoes__retirado_por', 'atividades__usuario', 'itens')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mala = self.object
        context['movimentacoes'] = mala.movimentacoes.all()
        context['atividades'] = mala.atividades.all()[:20]
        context['movimentacao_ativa'] = next((m for m in context['movimentacoes'] if m.esta_ativa), None)
        context['titulo_pagina'] = f"Painel de Controle: {mala.nome}"
        return context

# Adicionado ViewFilialScopedMixin por consistência
class MalaCreateView(LoginRequiredMixin, ViewFilialScopedMixin, AtividadeLogMixin, CreateView):
    model = MalaFerramentas
    form_class = MalaFerramentasForm
    template_name = 'ferramentas/mala_form.html'

    def form_valid(self, form):
        # A lógica de atribuição da filial já está correta
        if self.request.user.is_superuser and self.request.session.get('active_filial_id'):
            form.instance.filial_id = self.request.session.get('active_filial_id')
        else:
            form.instance.filial = self.request.user.filial_ativa
        
        response = super().form_valid(form)
        self._log_atividade(
            mala=self.object,
            tipo=Atividade.TipoAtividade.CRIACAO,
            descricao=f"Mala '{self.object.nome}' registrada."
        )
        messages.success(self.request, "Mala de ferramentas criada com sucesso.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

class MalaUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, AtividadeLogMixin, UpdateView):
    model = MalaFerramentas
    form_class = MalaFerramentasForm
    template_name = 'ferramentas/mala_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        self._log_atividade(
            mala=self.object,
            tipo=Atividade.TipoAtividade.ALTERACAO,
            descricao=f"Dados da mala '{self.object.nome}' foram atualizados."
        )
        messages.success(self.request, "Dados da mala atualizados com sucesso.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

# =============================================================================
# == VIEWS DE AÇÕES (Retirada, Devolução, Manutenção, etc.)
# =============================================================================

class AcaoFerramentaBaseView(LoginRequiredMixin, AtividadeLogMixin, View):
    """ View base para ações POST. A segurança é garantida no método get_ferramenta. """
    def get_ferramenta(self):
        # A filtragem por filial já está corretamente implementada aqui
        qs = Ferramenta.objects.for_request(self.request)
        return get_object_or_404(qs, pk=self.kwargs['pk'])

class IniciarManutencaoView(AcaoFerramentaBaseView):
    def post(self, request, *args, **kwargs):
        ferramenta = self.get_ferramenta()
        if ferramenta.status == Ferramenta.Status.DISPONIVEL:
            ferramenta.status = Ferramenta.Status.EM_MANUTENCAO
            ferramenta.save()
            self._log_atividade(ferramenta, Atividade.TipoAtividade.MANUTENCAO_INICIO, "Parada para manutenção iniciada.")
            messages.success(request, f"'{ferramenta.nome}' foi colocada em manutenção.")
        else:
            messages.error(request, "Ação não permitida. A ferramenta precisa estar 'Disponível'.")
        return redirect(ferramenta.get_absolute_url())

class FinalizarManutencaoView(AcaoFerramentaBaseView):
    def post(self, request, *args, **kwargs):
        ferramenta = self.get_ferramenta()
        if ferramenta.status == Ferramenta.Status.EM_MANUTENCAO:
            ferramenta.status = Ferramenta.Status.DISPONIVEL
            ferramenta.save()
            self._log_atividade(ferramenta, Atividade.TipoAtividade.MANUTENCAO_FIM, "Manutenção finalizada.")
            messages.success(request, f"A manutenção de '{ferramenta.nome}' foi finalizada.")
        else:
            messages.error(request, "Ação não permitida. A ferramenta precisa estar 'Em Manutenção'.")
        return redirect(ferramenta.get_absolute_url())

class InativarFerramentaView(AcaoFerramentaBaseView):
    def post(self, request, *args, **kwargs):
        ferramenta = self.get_ferramenta()
        if ferramenta.status == Ferramenta.Status.DISPONIVEL:
            ferramenta.status = Ferramenta.Status.DESCARTADA
            ferramenta.save()
            # Ajuste para tipo de atividade como string, conforme a implementação anterior
            self._log_atividade(ferramenta=ferramenta, tipo="descarte", descricao=f"Ferramenta marcada como descartada/inativa.")
            messages.success(request, f"'{ferramenta.nome}' foi inativada com sucesso.")
            return redirect('ferramentas:ferramenta_list')
        else:
            messages.error(request, "Ação não permitida. A ferramenta precisa estar 'Disponível' para ser inativada.")
            return redirect(ferramenta.get_absolute_url())

# =============================================================================
# == VIEWS DE MOVIMENTAÇÃO (ATUALIZADO)
# =============================================================================

class MovimentacaoCreateView(LoginRequiredMixin, AtividadeLogMixin, CreateView):
    model = Movimentacao
    form_class = MovimentacaoForm
    template_name = 'ferramentas/retirada_form.html'

    def dispatch(self, request, *args, **kwargs):
        """ Identifica se a retirada é de uma ferramenta ou de uma mala, aplicando o filtro de filial. """
        self.ferramenta = None
        self.mala = None
        
        if 'ferramenta_pk' in self.kwargs:
            qs = Ferramenta.objects.for_request(self.request)
            self.ferramenta = get_object_or_404(qs, pk=self.kwargs['ferramenta_pk'])
        elif 'mala_pk' in self.kwargs:
            qs = MalaFerramentas.objects.for_request(self.request)
            self.mala = get_object_or_404(qs, pk=self.kwargs['mala_pk'])
        
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ferramenta'] = self.ferramenta
        kwargs['mala'] = self.mala
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item'] = self.ferramenta or self.mala
        context['titulo_pagina'] = f"Checklist de Retirada: {context['item'].nome}"
        return context

    @transaction.atomic
    def form_valid(self, form):
        item = self.ferramenta or self.mala
        if item.status != 'disponivel':
            messages.error(self.request, f"'{item.nome}' não está disponível para retirada.")
            return redirect(item.get_absolute_url())

        movimentacao = form.save(commit=False)
        movimentacao.filial = self.request.user.filial_ativa

        assinatura_data = form.cleaned_data.get('assinatura_base64')
        if assinatura_data:
            format, imgstr = assinatura_data.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f'sig_ret_{item.pk}_{timezone.now().timestamp()}.{ext}'
            movimentacao.assinatura_retirada = ContentFile(base64.b64decode(imgstr), name=file_name)

        movimentacao.save()
        
        item.status = 'em_uso'
        item.save(update_fields=['status'])

        log_message = f"Retirada por {movimentacao.retirado_por.get_username()}."
        self._log_atividade(
            tipo=Atividade.TipoAtividade.RETIRADA,
            descricao=log_message,
            ferramenta=self.ferramenta,
            mala=self.mala
        )
        
        messages.success(self.request, f"'{item.nome}' retirada com sucesso.")
        return redirect(item.get_absolute_url())

# Adicionado ViewFilialScopedMixin
class DevolucaoUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, AtividadeLogMixin, UpdateView):
    model = Movimentacao
    form_class = DevolucaoForm
    template_name = 'ferramentas/devolucao_form.html'
    context_object_name = 'movimentacao'
    
    def get_queryset(self):
        # Garante que só pegamos devoluções de ferramentas individuais E da filial correta (via mixin)
        return super().get_queryset().filter(ferramenta__isnull=False)

    @transaction.atomic
    def form_valid(self, form):
        movimentacao = form.save(commit=False)
        movimentacao.data_devolucao = timezone.now()
        movimentacao.recebido_por = self.request.user
        # TODO: Adicionar lógica de salvamento de assinatura de devolução, se houver
        movimentacao.save()
        
        ferramenta = movimentacao.ferramenta
        ferramenta.status = Ferramenta.Status.DISPONIVEL
        ferramenta.save(update_fields=['status'])

        self._log_atividade(
            ferramenta=ferramenta,
            tipo=Atividade.TipoAtividade.DEVOLUCAO,
            descricao=f"Devolvida. Responsável pela retirada: {movimentacao.retirado_por.get_username()}."
        )
        messages.success(self.request, f"'{ferramenta.nome}' devolvida com sucesso.")
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return self.object.ferramenta.get_absolute_url()

# =============================================================================
# == VIEWS DE AÇÃO PARA MALAS (Refatorado)
# =============================================================================
# A view MovimentacaoCreateView agora lida com a retirada de Malas também,
# tornando MalaRetiradaCreateView redundante. Pode ser removida se a URL
# apontar para MovimentacaoCreateView com 'mala_pk'.
# Mantendo aqui por referência, caso a lógica precise ser separada no futuro.

class MalaRetiradaCreateView(LoginRequiredMixin, AtividadeLogMixin, CreateView):
    # Esta view pode ser substituída por MovimentacaoCreateView
    ...

# Adicionado ViewFilialScopedMixin
class MalaDevolucaoUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, AtividadeLogMixin, UpdateView):
    model = Movimentacao
    form_class = DevolucaoForm
    template_name = 'ferramentas/mala_devolucao_form.html'
    context_object_name = 'movimentacao'

    def get_queryset(self):
        # Filtra por movimentações de malas da filial correta
        return super().get_queryset().filter(mala__isnull=False)

    @transaction.atomic
    def form_valid(self, form):
        movimentacao = form.save(commit=False)
        movimentacao.data_devolucao = timezone.now()
        movimentacao.recebido_por = self.request.user
        # TODO: Adicionar lógica de salvamento de assinatura de devolução
        movimentacao.save()
        
        mala = movimentacao.mala
        mala.status = MalaFerramentas.Status.DISPONIVEL
        mala.save(update_fields=['status'])
        # Apenas ferramentas que não estão em manutenção podem voltar a ficar disponíveis
        mala.itens.exclude(status=Ferramenta.Status.EM_MANUTENCAO).update(status=Ferramenta.Status.DISPONIVEL)

        self._log_atividade(
            mala=mala,
            tipo=Atividade.TipoAtividade.DEVOLUCAO,
            descricao=f"Devolvida. Responsável: {movimentacao.retirado_por.get_username()}."
        )
        messages.success(self.request, f"Mala '{mala.nome}' devolvida com sucesso.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.object.mala.get_absolute_url()

# =============================================================================
# == VIEWS DE IMPORTAÇÃO E UTILITÁRIOS
# =============================================================================

# Não precisa de mixin de filial, pois não lida com objetos do banco
class DownloadTemplateView(LoginRequiredMixin, View):
    """
    Gera e oferece para download a planilha modelo formatada para o usuário preencher.
    """
    def get(self, request, *args, **kwargs):
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Modelo de Importação"
        # --- Estilos do Cabeçalho ---
        header_font = Font(name='Calibri', bold=True, color='FFFFFF', size=12)
        header_fill = PatternFill(start_color='004C99', end_color='004C99', fill_type='solid') # Tom de azul escuro
        header_alignment = Alignment(horizontal='center', vertical='center')
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        # --- Cabeçalhos das Colunas ---
        headers = [
            "Nome da Ferramenta*", "Código de Identificação* (para QR Code)",
            "Data de Aquisição (dd/mm/aaaa)*", "Localização Padrão*", "Nº de Patrimônio",
            "Fabricante", "Modelo", "Série", "Tamanho da Polegada", "Numero Laudo técnico",
            "Mala", "Filial", "quantidade", "Observações", 
        ]
        
        # Aplica os cabeçalhos e estilos
        for col_num, header_title in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.value = header_title
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
            column_letter = get_column_letter(col_num)
            worksheet.column_dimensions[column_letter].width = 30

        # Prepara a resposta HTTP para o download
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="modelo_importacao_ferramentas.xlsx"'
        workbook.save(response)
        return response

# Não precisa de mixin, pois a lógica da filial é tratada no form_valid
class ImportarFerramentasView(LoginRequiredMixin, FormView):
    """
    View que renderiza a página de upload e processa a planilha enviada.
    """
    template_name = 'ferramentas/importar_ferramentas.html'
    form_class = UploadFileForm
    success_url = reverse_lazy('ferramentas:ferramenta_list')

    def form_valid(self, form):
        file = form.cleaned_data['file']
        active_filial_id = self.request.session.get('active_filial_id')

        if not active_filial_id:
            messages.error(self.request, "Nenhuma filial ativa selecionada. Por favor, selecione uma filial antes de importar.")
            return self.form_invalid(form)

        try:
            workbook = openpyxl.load_workbook(file)
            worksheet = workbook.active
            ferramentas_para_criar, erros = [], []
            codigos_ja_processados = set()
            
            # Adicionamos max_col=13 para forçar a leitura de todas as 13 colunas
            for i, row in enumerate(worksheet.iter_rows(min_row=2, max_col=13, values_only=True), start=2):
                if all(cell is None for cell in row):
                    continue

                (
                    nome, codigo, data_str, localizacao, patrimonio, fabricante, 
                    modelo, serie, tamanho, laudo, mala_nome, filial_nome, observacoes
                ) = row

                if not all([nome, codigo, data_str, localizacao]):
                    erros.append(f"Linha {i}: Dados obrigatórios faltando (Nome, Código, Data ou Localização).")
                    continue
                
                codigo = str(codigo).strip()
                if codigo in codigos_ja_processados:
                    erros.append(f"Linha {i}: O Código de Identificação '{codigo}' está duplicado na planilha.")
                    continue
                
                try:
                    if isinstance(data_str, datetime):
                        data_aquisicao = data_str.date()
                    else:
                        data_aquisicao = datetime.strptime(str(data_str).split(" ")[0], '%d/%m/%Y').date()
                except (ValueError, TypeError):
                    erros.append(f"Linha {i}: Formato de data inválido para '{data_str}'. Use dd/mm/aaaa.")
                    continue

                if Ferramenta.objects.filter(codigo_identificacao=codigo).exists():
                    erros.append(f"Linha {i}: Código de Identificação '{codigo}' já existe no sistema.")
                    continue
                
                filial_obj = None
                if filial_nome:
                    try:
                        filial_obj = Filial.objects.get(nome__iexact=str(filial_nome).strip())
                    except Filial.DoesNotExist:
                        erros.append(f"Linha {i}: A filial '{filial_nome}' não foi encontrada no sistema.")
                        continue
                else:
                    filial_obj = Filial.objects.get(pk=active_filial_id)

                mala_obj = None
                if mala_nome:
                    try:
                        mala_obj = MalaFerramentas.objects.get(nome__iexact=str(mala_nome).strip(), filial=filial_obj)
                    except MalaFerramentas.DoesNotExist:
                        erros.append(f"Linha {i}: A mala '{mala_nome}' não foi encontrada na filial '{filial_obj.nome}'.")
                        continue

                ferramentas_para_criar.append(Ferramenta(
                    nome=nome, codigo_identificacao=codigo.upper(), data_aquisicao=data_aquisicao,
                    localizacao_padrao=localizacao, patrimonio=(patrimonio or None),
                    fabricante_marca=(fabricante or None), modelo=(modelo or None), serie=(serie or None),
                    tamanho_polegadas=(tamanho or None), numero_laudo_tecnico=(laudo or None),
                    mala=mala_obj, filial=filial_obj, observacoes=(observacoes or None)
                ))
                codigos_ja_processados.add(codigo)

            if erros:
                for erro in erros:
                    messages.error(self.request, erro)
                return self.form_invalid(form)

            with transaction.atomic():
                Ferramenta.objects.bulk_create(ferramentas_para_criar)

            messages.success(self.request, f"{len(ferramentas_para_criar)} ferramentas importadas com sucesso!")
        except Exception as e:
            messages.error(self.request, f"Ocorreu um erro inesperado ao processar o arquivo: {e}")
            return self.form_invalid(form)

        return super().form_valid(form)
    
class ImprimirQRCodesView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Ferramenta
    template_name = 'ferramentas/imprimir_qrcodes.html'
    context_object_name = 'ferramentas'

    def get_queryset(self):
        # O mixin já filtra pela filial, então apenas adicionamos o resto da lógica
        return super().get_queryset().exclude(
            status=Ferramenta.Status.DESCARTADA
        ).filter(
            qr_code__isnull=False
        ).exclude(
            qr_code=''
        ).order_by('nome')

# Adicionado ViewFilialScopedMixin para segurança
class ResultadoScanView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Ferramenta
    template_name = 'ferramentas/resultado_scan.html'
    context_object_name = 'ferramenta'
    slug_field = 'codigo_identificacao'
    slug_url_kwarg = 'codigo_identificacao'
    
    # O get_queryset será tratado pelo mixin

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ferramenta = self.object
        context['movimentacao_ativa'] = ferramenta.movimentacoes.filter(data_devolucao__isnull=True).first()
        return context
    
class GerarQRCodesView(LoginRequiredMixin, SSTPermissionMixin, View):
    """
    Aciona o comando de gerenciamento `generate_qrcodes` em segundo plano.
    """
    permission_required = 'ferramentas.change_ferramenta'

    def post(self, request, *args, **kwargs):
        command = [
            sys.executable,
            str(settings.BASE_DIR / "manage.py"),
            "generate_qrcodes",
        ]
        subprocess.Popen(command)
        messages.success(
            request, 
            "A geração de QR Codes foi iniciada em segundo plano. Os novos QR Codes aparecerão na lista em breve."
        )
        return redirect('ferramentas:ferramenta_list')
    
# =============================================================================
# == VIEWS DE TERMO DE RESPONSABILIDADE
# =============================================================================

# Refatorado para incluir mixins de segurança e filtrar por filial
class CriarTermoResponsabilidadeView(LoginRequiredMixin, ViewFilialScopedMixin, FormView):
    template_name = 'ferramentas/termo_responsabilidade_form.html'
    form_class = TermoResponsabilidadeForm
    success_url = reverse_lazy('ferramentas:ferramenta_list') # Ajuste a URL de sucesso conforme necessário


    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request # Passa o request para o __init__ do form
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ferramentas'] = Ferramenta.objects.for_request(self.request).filter(status=Ferramenta.Status.DISPONIVEL)
        context['malas'] = MalaFerramentas.objects.for_request(self.request).filter(status=MalaFerramentas.Status.DISPONIVEL)
        return context
    
    # Ajuste final: redirecionar para a nova página de detalhes após criar
    def get_success_url(self):
        # 'self.object' não é definido em FormView, então precisamos pegar o 'termo' do form_valid.
        # Uma forma mais robusta é salvar o pk na sessão ou refatorar, mas por simplicidade,
        # vamos redirecionar para a lista por enquanto.
        # Para o redirecionamento da sua pergunta funcionar, você precisaria salvar o termo no self.
        return reverse_lazy('ferramentas:ferramenta_list')

    @transaction.atomic
    def form_valid(self, form):
        assinatura_base64 = self.request.POST.get('assinatura_base64')
        if not assinatura_base64:
            form.add_error(None, "É obrigatório que o responsável assine o termo.")
            return self.form_invalid(form)

        try:
            itens_processados = json.loads(self.request.POST.get('itens_termo_json', '[]'))
            if not itens_processados:
                messages.error(self.request, "Nenhum item foi selecionado para o termo.")
                return self.form_invalid(form)
        except json.JSONDecodeError:
            messages.error(self.request, "Erro ao processar os itens do termo. Tente novamente.")
            return self.form_invalid(form)

        # 1. Salva o Termo de Responsabilidade principal
        termo = form.save(commit=False)
        termo.movimentado_por = self.request.user
        termo.assinatura_data = assinatura_base64
        termo.data_recebimento = timezone.now()
        termo.filial = self.request.user.filial_ativa
        termo.save()

        # Data de devolução padrão (ex: 7 dias), você pode tornar isso um campo no form depois
        data_devolucao = timezone.now() + timedelta(days=7)

        # 2. Itera sobre cada item selecionado para criar registros e atualizar status
        for item_data in itens_processados:
            item_pk = item_data.get('pk')
            if not item_pk: continue

            item_obj = None
            ferramenta_obj, mala_obj = None, None

            # Identifica o item (Ferramenta ou Mala)
            if termo.tipo_uso == TermoDeResponsabilidade.TipoUso.FERRAMENTAL:
                ferramenta_obj = get_object_or_404(Ferramenta, pk=item_pk)
                item_obj = ferramenta_obj
            elif termo.tipo_uso == TermoDeResponsabilidade.TipoUso.MALA:
                mala_obj = get_object_or_404(MalaFerramentas, pk=item_pk)
                item_obj = mala_obj
            
            # Valida se o item ainda está disponível
            if item_obj.status != 'disponivel':
                messages.error(self.request, f"O item '{item_obj}' não está mais disponível para retirada.")
                # A transação será revertida, cancelando a criação do termo.
                return self.form_invalid(form)

            # 2a. Cria o ItemTermo (relação entre Termo e o item)
            ItemTermo.objects.create(
                termo=termo,
                ferramenta=ferramenta_obj,
                mala=mala_obj,
                quantidade=item_data['quantidade'],
                unidade=item_data['unidade'],
                item=item_data['item']
            )

            # 2b. Cria a Movimentacao (o registro de "retirada")
            Movimentacao.objects.create(
                termo_responsabilidade=termo,  # Link para o termo
                ferramenta=ferramenta_obj,
                mala=mala_obj,
                # NOTA: 'retirado_por' é um Usuário, 'responsavel' é um Funcionário.
                # Usamos o usuário que está logado e operando o sistema.
                retirado_por=termo.movimentado_por,
                data_devolucao_prevista=data_devolucao,
                condicoes_retirada="Retirada conforme Termo de Responsabilidade #" + str(termo.pk),
                filial=termo.filial
            )

            # 2c. Atualiza o status do item para "Em Uso"
            item_obj.status = 'em_uso'
            item_obj.save(update_fields=['status'])

            # 2d. (Opcional, mas recomendado) Cria um log de Atividade
            Atividade.objects.create(
                ferramenta=ferramenta_obj,
                mala=mala_obj,
                tipo_atividade=Atividade.TipoAtividade.RETIRADA,
                descricao=f"Retirada por {termo.responsavel} via Termo #{termo.pk}.",
                usuario=self.request.user,
                filial=termo.filial
            )

        messages.success(self.request, f"Termo de Responsabilidade #{termo.pk} criado e itens retirados com sucesso.")
        
        # ARMAZENA O TERMO CRIADO NO SELF PARA USAR NO GET_SUCCESS_URL
        self.termo_criado = termo
        
        return super().form_valid(form)

    # Nova implementação do get_success_url que usa o objeto salvo
    def get_success_url(self):
        return reverse('ferramentas:termo_detail', kwargs={'pk': self.termo_criado.pk})
        
# Para listar todos os termos
class TermoListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = TermoDeResponsabilidade
    template_name = 'ferramentas/termo_list.html' # Crie este template simples
    context_object_name = 'termos'
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related('responsavel', 'filial').order_by('-data_emissao')

# VIEW ATUALIZADA: TermoDetailView agora renderiza o template de PDF

class TermoDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    """
    Exibe os detalhes de um Termo de Responsabilidade.
    """
    model = TermoDeResponsabilidade
    template_name = 'ferramentas/termo_detail.html'  # Precisaremos criar este template
    context_object_name = 'termo'

    def get_queryset(self):
        # Otimiza a consulta buscando itens e ferramentas/malas relacionadas
        return super().get_queryset().prefetch_related(
            'itens__ferramenta', 'itens__mala'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        termo = self.get_object()
        
        # Verifica se ALGUMA movimentação gerada por este termo JÁ foi devolvida.
        # Se sim, o termo não pode mais ser revertido de forma completa.
        movimentacoes_devolvidas = termo.movimentacoes_geradas.filter(data_devolucao__isnull=False).exists()
        
        # Passa uma flag para o template para saber se pode mostrar o botão de reverter
        context['pode_reverter'] = not movimentacoes_devolvidas
        
        context['titulo_pagina'] = f"Termo de Responsabilidade #{termo.pk}"
        return context

class ReverterTermoView(LoginRequiredMixin, ViewFilialScopedMixin, View):
    """
    Processa a reversão (estorno) de um Termo de Responsabilidade.
    Esta view só aceita requisições POST.
    """
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Pega o termo da filial correta para garantir a segurança
        termo = get_object_or_404(TermoDeResponsabilidade.objects.for_request(request), pk=self.kwargs['pk'])

        # Busca todas as movimentações ATIVAS geradas por este termo
        movimentacoes_ativas = termo.movimentacoes_geradas.filter(data_devolucao__isnull=True)

        if not movimentacoes_ativas.exists():
            messages.warning(request, "Este termo não possui itens ativos para reverter.")
            return redirect('ferramentas:termo_detail', pk=termo.pk)

        # Itera sobre cada movimentação ativa para reverter
        for mov in movimentacoes_ativas:
            item_a_devolver = mov.ferramenta or mov.mala

            if item_a_devolver:
                # 1. Devolve o item, marcando seu status como 'disponivel'
                # Apenas se não estiver em manutenção
                if item_a_devolver.status != 'em_manutencao':
                    item_a_devolver.status = 'disponivel'
                    item_a_devolver.save(update_fields=['status'])

                # 2. Finaliza a movimentação
                mov.data_devolucao = timezone.now()
                mov.recebido_por = request.user
                mov.condicoes_devolucao = f"Devolução automática via estorno do Termo #{termo.pk}."
                mov.save()

        # 3. Cria um log de atividade para o termo
        Atividade.objects.create(
            # Embora não tenha um campo direto, podemos usar a descrição
            descricao=f"Termo #{termo.pk} revertido/estornado por {request.user.get_username()}.",
            tipo_atividade=Atividade.TipoAtividade.DEVOLUCAO, 
            usuario=request.user,
            filial=termo.filial
        )

        messages.success(request, f"Termo #{termo.pk} revertido com sucesso. Todos os itens foram devolvidos.")
        return redirect('ferramentas:termo_detail', pk=termo.pk)

# NOVA VIEW: Para download do PDF individual
class DownloadTermoPDFView(LoginRequiredMixin, ViewFilialScopedMixin, View):
    def get(self, request, *args, **kwargs):
        termo = get_object_or_404(TermoDeResponsabilidade.objects.for_request(request), pk=self.kwargs['pk'])
        html_string = render_to_string('ferramentas/termo_pdf_template.html', {'termo': termo})
        
        # Correção para WeasyPrint em ambientes de produção (Windows)
        with tempfile.NamedTemporaryFile(delete=True, suffix='.html') as temp_html:
            temp_html.write(html_string.encode('UTF-8'))
            temp_html.flush()
            with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as temp_pdf:
                subprocess.run(['weasyprint', temp_html.name, temp_pdf.name])
                temp_pdf.seek(0)
                pdf = temp_pdf.read()

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="termo_{termo.pk}_{termo.responsavel}.pdf"'
        return response

# NOVA VIEW: Para download de múltiplos PDFs em um arquivo ZIP
class DownloadTermosLoteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        termos_ids = request.POST.getlist('termo_ids')
        if not termos_ids:
            messages.warning(request, "Nenhum termo selecionado para download.")
            return redirect('ferramentas:termo_list')

        qs = TermoDeResponsabilidade.objects.for_request(request).filter(pk__in=termos_ids)
        
        # Cria um arquivo ZIP em memória
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for termo in qs:
                html_string = render_to_string('ferramentas/termo_pdf_template.html', {'termo': termo})
                
                with tempfile.NamedTemporaryFile(delete=True, suffix='.html') as temp_html:
                    temp_html.write(html_string.encode('UTF-8'))
                    temp_html.flush()
                    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as temp_pdf:
                        subprocess.run(['weasyprint', temp_html.name, temp_pdf.name])
                        temp_pdf.seek(0)
                        pdf = temp_pdf.read()
                
                pdf_filename = f'termo_{termo.pk}_{termo.responsavel}.pdf'
                zip_file.writestr(pdf_filename, pdf)
        
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="termos_responsabilidade.zip"'

        return response
    
