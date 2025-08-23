
# ferramentas/views.py

# --- Imports do Python ---
import base64
import json
from datetime import timedelta
from io import BytesIO

# --- Imports do Django ---
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
# --- Imports Locais ---
from .models import Ferramenta, Movimentacao, Atividade
from .forms import FerramentaForm, RetiradaForm, DevolucaoForm
from core.mixins import ViewFilialScopedMixin


# =============================================================================
# == MIXINS REUTILIZÁVEIS
# =============================================================================

class AtividadeLogMixin:
    """
    Mixin que fornece um método helper para criar logs de atividade,
    evitando repetição de código nas views.
    """
    def _log_atividade(self, ferramenta, tipo, descricao):
        Atividade.objects.create(
            ferramenta=ferramenta,
            filial=ferramenta.filial, # Garante que o log também tenha a filial
            tipo_atividade=tipo,
            descricao=descricao,
            usuario=self.request.user
        )
# =============================================================================
# == VIEWS PRINCIPAIS
# =============================================================================
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'ferramentas/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request # Usar o request diretamente

        # Usa .for_request() para filtrar os dados do dashboard
        ferramentas_da_filial = Ferramenta.objects.for_request(request)
        movimentacoes_da_filial = Movimentacao.objects.for_request(request)
        atividades_da_filial = Atividade.objects.for_request(request)

        status_counts = ferramentas_da_filial.values('status').annotate(total=Count('status'))
        
        context['stats'] = {item['status']: item['total'] for item in status_counts}
        context['stats']['total'] = ferramentas_da_filial.count()

        context['ferramentas_em_uso'] = movimentacoes_da_filial.filter(data_devolucao__isnull=True).select_related('ferramenta', 'retirado_por')
        context['ferramentas_em_manutencao'] = ferramentas_da_filial.filter(status=Ferramenta.Status.EM_MANUTENCAO)
        context['ultimas_atividades'] = atividades_da_filial.order_by('-timestamp')[:5]
        
        context['titulo_pagina'] = "Dashboard de Operações"
        return context

class FerramentaListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Ferramenta
    template_name = 'ferramentas/ferramenta_list.html'
    context_object_name = 'ferramentas'
    # A queryset base é definida aqui. O FilialScopedMixin aplicará o filtro por cima.
    queryset = Ferramenta.objects.exclude(status=Ferramenta.Status.DESCARTADA).order_by('nome')

class FerramentaDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Ferramenta
    template_name = 'ferramentas/ferramenta_detail.html'
    context_object_name = 'ferramenta'
    
    def get_queryset(self):
        # Chama super().get_queryset() sem argumentos.
        # O mixin já cuida da filtragem. Adicionamos o prefetch para otimização.
        return super().get_queryset().prefetch_related(
            'movimentacoes__retirado_por', 
            'movimentacoes__recebido_por',
            'atividades__usuario'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ferramenta = self.object
        
        context['movimentacoes'] = ferramenta.movimentacoes.all()
        context['atividades'] = ferramenta.atividades.all()[:10]
        context['movimentacao_ativa'] = next((m for m in context['movimentacoes'] if m.esta_ativa), None)

        # Lógica do Gráfico (sem alterações)
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

class FerramentaCreateView(LoginRequiredMixin, AtividadeLogMixin, CreateView):
    model = Ferramenta
    form_class = FerramentaForm
    template_name = 'ferramentas/ferramenta_form.html'

    def form_valid(self, form):
        # MELHORIA: Se o usuário for superuser e tiver uma filial ativa na sessão, usa essa.
        # Senão, usa a filial do próprio usuário.
        if self.request.user.is_superuser and self.request.session.get('active_filial_id'):
            form.instance.filial_id = self.request.session.get('active_filial_id')
        else:
            form.instance.filial = self.request.user.filial
        
        messages.success(self.request, "Ferramenta adicionada com sucesso.")
        response = super().form_valid(form) 
        self._log_atividade(self.object, Atividade.TipoAtividade.CRIACAO, f"Ferramenta '{self.object.nome}' registrada.")
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
        self._log_atividade(self.object, Atividade.TipoAtividade.ALTERACAO, "Dados da ferramenta foram atualizados.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar: {self.object.nome}"
        return context
    
# =============================================================================
# == VIEWS DE AÇÕES (Retirada, Devolução, Manutenção, etc.)
# =============================================================================

class AcaoFerramentaBaseView(LoginRequiredMixin, AtividadeLogMixin, View):
    """ View base para ações POST. Agora usa .for_request(). """
    def get_ferramenta(self):
        # CORREÇÃO: Usa .for_request() para segurança
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
            self._log_atividade(ferramenta, "Descarte", f"Ferramenta marcada como descartada/inativa.")
            messages.success(request, f"'{ferramenta.nome}' foi inativada com sucesso.")
            return redirect('ferramentas:ferramenta_list')
        else:
            messages.error(request, "Ação não permitida. A ferramenta precisa estar 'Disponível' para ser inativada.")
            return redirect(ferramenta.get_absolute_url())

class RetiradaCreateView(LoginRequiredMixin, AtividadeLogMixin, CreateView):
    model = Movimentacao
    form_class = RetiradaForm
    template_name = 'ferramentas/retirada_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # CORREÇÃO: Usa .for_request()
        qs = Ferramenta.objects.for_request(self.request)
        context['ferramenta'] = get_object_or_404(qs, pk=self.kwargs['ferramenta_pk'])
        context['titulo_pagina'] = f"Retirar Ferramenta: {context['ferramenta'].nome}"
        return context

    @transaction.atomic
    def form_valid(self, form):
        # CORREÇÃO: Usa .for_request()
        qs = Ferramenta.objects.for_request(self.request)
        ferramenta = get_object_or_404(qs, pk=self.kwargs['ferramenta_pk'])
        if ferramenta.status != Ferramenta.Status.DISPONIVEL:
            messages.error(self.request, "Esta ferramenta não está disponível para retirada.")
            return redirect(self.get_success_url())

        movimentacao = form.save(commit=False)
        movimentacao.ferramenta = ferramenta
        movimentacao.filial = self.request.user.filial # Associa a movimentação à filial

        # Processamento da assinatura...
        assinatura_data = form.cleaned_data.get('assinatura_base64')
        if assinatura_data:
            format, imgstr = assinatura_data.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f'sig_ret_{ferramenta.pk}_{timezone.now().timestamp()}.{ext}'
            movimentacao.assinatura_retirada = ContentFile(base64.b64decode(imgstr), name=file_name)
        
        movimentacao.save()
        ferramenta.status = Ferramenta.Status.EM_USO
        ferramenta.save(update_fields=['status'])

        self._log_atividade(ferramenta, Atividade.TipoAtividade.RETIRADA, f"Retirada por {movimentacao.retirado_por.get_username()}.")
        messages.success(self.request, f"'{ferramenta.nome}' retirada com sucesso.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('ferramentas:ferramenta_detail', kwargs={'pk': self.kwargs['ferramenta_pk']})


class DevolucaoUpdateView(LoginRequiredMixin, AtividadeLogMixin, UpdateView):
    model = Movimentacao
    form_class = DevolucaoForm
    template_name = 'ferramentas/devolucao_form.html'
    context_object_name = 'movimentacao'
    
    def get_queryset(self):
        # CORREÇÃO: Usa .for_request()
        return Movimentacao.objects.for_request(self.request)

    @transaction.atomic
    def form_valid(self, form):
        movimentacao = form.save(commit=False)
        movimentacao.data_devolucao = timezone.now()
        movimentacao.recebido_por = self.request.user

        # Processamento da assinatura...
        assinatura_data = form.cleaned_data.get('assinatura_base64')
        if assinatura_data:
            format, imgstr = assinatura_data.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f'sig_dev_{movimentacao.ferramenta.pk}_{timezone.now().timestamp()}.{ext}'
            movimentacao.assinatura_devolucao = ContentFile(base64.b64decode(imgstr), name=file_name)
        
        movimentacao.save()
        
        ferramenta = movimentacao.ferramenta
        ferramenta.status = Ferramenta.Status.DISPONIVEL
        ferramenta.save(update_fields=['status'])

        self._log_atividade(ferramenta, Atividade.TipoAtividade.DEVOLUCAO, f"Devolvida por {movimentacao.retirado_por.get_username()}.")
        messages.success(self.request, f"'{ferramenta.nome}' devolvida com sucesso.")
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return self.object.ferramenta.get_absolute_url()
