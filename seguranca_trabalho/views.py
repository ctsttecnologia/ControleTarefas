# seguranca_trabalho/views.py (REFATORADO)

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.http import HttpResponse

from .models import Equipamento, FichaEPI, EntregaEPI, MovimentacaoEstoque
from .forms import EquipamentoForm, FichaEPIForm, EntregaEPIForm, AssinaturaForm



class EquipamentoListView(LoginRequiredMixin, ListView):
    model = Equipamento
    template_name = 'seguranca_trabalho/equipamento_list.html'
    context_object_name = 'equipamentos'
    paginate_by = 10

class EquipamentoCreateView(LoginRequiredMixin, CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')

    def form_valid(self, form):
        messages.success(self.request, "Equipamento cadastrado com sucesso!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Cadastrar Novo Equipamento (EPI)'
        return context

class EquipamentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')

    def form_valid(self, form):
        messages.success(self.request, "Equipamento atualizado com sucesso!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Equipamento: {self.object.nome}"
        return context

class DashboardSSTView(LoginRequiredMixin, ListView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Dashboard de Saúde e Segurança'
        # Adicionar KPIs aqui, ex:
        context['total_fichas_ativas'] = FichaEPI.objects.filter(colaborador=True).count()
        context['entregas_pendentes_assinatura'] = EntregaEPI.objects.filter(assinatura_recebimento='').count()
        return context

class FichaEPIListView(LoginRequiredMixin, ListView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_lista.html'
    context_object_name = 'fichas'
    paginate_by = 10

class FichaEPICreateView(LoginRequiredMixin, CreateView):
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_criar_form.html'
    
    def get_success_url(self):
        return reverse_lazy('seguranca_trabalho:ficha_detalhe', kwargs={'pk': self.object.pk})
        
    def form_valid(self, form):
        messages.success(self.request, "Ficha de EPI criada com sucesso!")
        return super().form_valid(form)

class FichaEPIDetailView(LoginRequiredMixin, DetailView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_detalhe.html'
    context_object_name = 'ficha'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entrega_form'] = EntregaEPIForm()
        context['assinatura_form'] = AssinaturaForm()
        return context

@login_required
@transaction.atomic
def adicionar_entrega(request, ficha_pk):
    ficha = get_object_or_404(FichaEPI, pk=ficha_pk)
    if request.method == 'POST':
        form = EntregaEPIForm(request.POST)
        if form.is_valid():
            equipamento = form.cleaned_data['equipamento']
            quantidade = form.cleaned_data['quantidade']
            
            if equipamento.estoque_atual < quantidade:
                messages.error(request, f"Estoque insuficiente para '{equipamento.nome}'. Apenas {equipamento.estoque_atual} em estoque.")
                return redirect('seguranca_trabalho:ficha_detalhe', pk=ficha_pk)

            entrega = form.save(commit=False)
            entrega.ficha = ficha
            entrega.save() # O 'save' do model já cuida da movimentação de SAÍDA
            messages.success(request, f"Entrega registrada. Aguardando assinatura do colaborador.")
    return redirect('seguranca_trabalho:ficha_detalhe', pk=ficha_pk)

@login_required
def assinar_entrega_recebimento(request, pk):
    entrega = get_object_or_404(EntregaEPI, pk=pk)
    if request.method == 'POST':
        form = AssinaturaForm(request.POST)
        if form.is_valid():
            entrega.assinatura_recebimento = form.cleaned_data['assinatura_base64']
            entrega.save(update_fields=['assinatura_recebimento'])
            messages.success(request, "Recebimento de EPI assinado com sucesso!")
    return redirect('seguranca_trabalho:ficha_detalhe', pk=entrega.ficha.pk)

@login_required
@transaction.atomic
def registrar_devolucao(request, pk):
    entrega = get_object_or_404(EntregaEPI, pk=pk)
    if request.method == 'POST':
        form = AssinaturaForm(request.POST)
        if form.is_valid():
            MovimentacaoEstoque.objects.create(
                equipamento=entrega.equipamento,
                tipo='ENTRADA',
                quantidade=entrega.quantidade,
                responsavel=request.user,
                justificativa=f'Devolução da Ficha #{entrega.ficha.pk}'
            )
            entrega.assinatura_devolucao = form.cleaned_data['assinatura_base64']
            entrega.data_devolucao = timezone.now()
            entrega.save(update_fields=['assinatura_devolucao', 'data_devolucao'])
            messages.success(request, "Devolução de EPI registrada e assinada!")
    return redirect('seguranca_trabalho:ficha_detalhe', pk=entrega.ficha.pk)

@login_required
def gerar_relatorio_ficha(request, pk):
    ficha = get_object_or_404(FichaEPI, pk=pk)
    # Adapte sua lógica de geração de PDF/Word para os novos modelos
    # Use os dados de `ficha` e `ficha.entregas.all()`
    return HttpResponse(f"Relatório para Ficha #{ficha.pk}", content_type='text/plain')
