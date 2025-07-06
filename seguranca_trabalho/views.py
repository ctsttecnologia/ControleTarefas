
# seguranca_trabalho/views.py

from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone

from .models import Equipamento, FichaEPI, EntregaEPI, Fabricante, Fornecedor, Funcao, MatrizEPI, MovimentacaoEstoque
from .forms import EquipamentoForm, FichaEPIForm, EntregaEPIForm, AssinaturaForm, FabricanteForm, FornecedorForm
from departamento_pessoal.models import Funcionario
import json


class SSTPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = 'auth.view_user' # Altere para a permissão correta de SST

# --- DASHBOARD ---
class DashboardSSTView(SSTPermissionMixin, TemplateView):
    template_name = 'seguranca_trabalho/dashboard.html'
    def get_context_data(self, **kwargs):
        # ... sua lógica de KPIs ...
        return super().get_context_data(**kwargs)

# --- CRUDs DE CATÁLOGO (Equipamento, Fabricante, Fornecedor) ---
class FabricanteListView(SSTPermissionMixin, ListView):
    model = Fabricante
    template_name = 'seguranca_trabalho/fabricante_list.html'

class FabricanteCreateView(SSTPermissionMixin, CreateView):
    model = Fabricante; form_class = FabricanteForm; template_name = 'seguranca_trabalho/fabricante_form.html'; success_url = reverse_lazy('seguranca_trabalho:fabricante_list')

class FabricanteUpdateView(SSTPermissionMixin, UpdateView):
    model = Fabricante; form_class = FabricanteForm; template_name = 'seguranca_trabalho/fabricante_form.html'; success_url = reverse_lazy('seguranca_trabalho:fabricante_list')

class FornecedorListView(SSTPermissionMixin, ListView):
    model = Fornecedor
    template_name = 'seguranca_trabalho/fornecedor_list.html'

class FornecedorCreateView(SSTPermissionMixin, CreateView):
    model = Fornecedor; form_class = FornecedorForm; template_name = 'seguranca_trabalho/fornecedor_form.html'; success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')

class FornecedorUpdateView(SSTPermissionMixin, UpdateView):
    model = Fornecedor; form_class = FornecedorForm; template_name = 'seguranca_trabalho/fornecedor_form.html'; success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')

class EquipamentoListView(SSTPermissionMixin, ListView):
    model = Equipamento; template_name = 'seguranca_trabalho/equipamento_list.html'; context_object_name = 'equipamentos'

class EquipamentoDetailView(SSTPermissionMixin, DetailView):
    model = Equipamento; template_name = 'seguranca_trabalho/equipamento_detail.html'

class EquipamentoCreateView(SSTPermissionMixin, CreateView):
    model = Equipamento; form_class = EquipamentoForm; template_name = 'seguranca_trabalho/equipamento_form.html'; success_url = reverse_lazy('seguranca_trabalho:equipamento_list')

class EquipamentoUpdateView(SSTPermissionMixin, UpdateView):
    model = Equipamento; form_class = EquipamentoForm; template_name = 'seguranca_trabalho/equipamento_form.html'; success_url = reverse_lazy('seguranca_trabalho:equipamento_list')

class EquipamentoDeleteView(SSTPermissionMixin, DeleteView):
    model = Equipamento; template_name = 'seguranca_trabalho/confirm_delete.html'; success_url = reverse_lazy('seguranca_trabalho:equipamento_list')

# --- CRUD DE FICHAS DE EPI ---
class FichaEPIListView(SSTPermissionMixin, ListView):
    model = FichaEPI; template_name = 'seguranca_trabalho/ficha_lista.html'; context_object_name = 'fichas'; queryset = FichaEPI.objects.select_related('funcionario__cargo')

class FichaEPICreateView(SSTPermissionMixin, CreateView):
    model = FichaEPI; form_class = FichaEPIForm; template_name = 'seguranca_trabalho/ficha_form.html'
    def get_success_url(self): return reverse_lazy('seguranca_trabalho:ficha_detalhe', kwargs={'pk': self.object.pk})

class FichaEPIDetailView(SSTPermissionMixin, DetailView):
    model = FichaEPI; template_name = 'seguranca_trabalho/ficha_detalhe.html'; context_object_name = 'ficha'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entrega_form'] = EntregaEPIForm(); context['assinatura_form'] = AssinaturaForm()
        return context

# --- VIEWS DE AÇÃO (PARA FORMULÁRIOS SECUNDÁRIOS) ---
class AdicionarEntregaView(SSTPermissionMixin, View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        ficha = get_object_or_404(FichaEPI, pk=self.kwargs.get('ficha_pk'))
        form = EntregaEPIForm(request.POST)
        if form.is_valid():
            entrega = form.save(commit=False); entrega.ficha = ficha; entrega.save()
            messages.success(request, "Entrega registrada. Aguardando assinatura.")
        else: messages.error(request, "Erro ao registrar entrega.")
        return redirect('seguranca_trabalho:ficha_detalhe', pk=ficha.pk)

class AssinarEntregaView(SSTPermissionMixin, View):
    def post(self, request, *args, **kwargs):
        entrega = get_object_or_404(EntregaEPI, pk=self.kwargs.get('pk'))
        form = AssinaturaForm(request.POST)
        if form.is_valid():
            entrega.assinatura_recebimento = form.cleaned_data['assinatura_base64']
            entrega.data_entrega = timezone.now()
            entrega.save(update_fields=['assinatura_recebimento', 'data_entrega'])
            messages.success(request, "Recebimento de EPI assinado!")
        return redirect('seguranca_trabalho:ficha_detalhe', pk=entrega.ficha.pk)

class RegistrarDevolucaoView(SSTPermissionMixin, View):
    def post(self, request, *args, **kwargs):
        # Implemente a lógica de devolução aqui
        entrega = get_object_or_404(EntregaEPI, pk=self.kwargs.get('pk'))
        entrega.data_devolucao = timezone.now()
        entrega.save(update_fields=['data_devolucao'])
        messages.success(request, "Devolução registrada com sucesso!")
        return redirect('seguranca_trabalho:ficha_detalhe', pk=entrega.ficha.pk)

# --- VIEWS DE API ---
class FuncaoDoColaboradorAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Implemente a lógica da API aqui
        return JsonResponse({})# seguranca_trabalho/views.py
    
class DashboardSSTView(LoginRequiredMixin, TemplateView):
    template_name = 'seguranca_trabalho/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Dashboard de Segurança do Trabalho'
        
        # --- KPIs (Indicadores Chave) ---
        context['total_equipamentos'] = Equipamento.objects.filter(ativo=True).count()
        context['fichas_ativas'] = FichaEPI.objects.filter(funcionario__status='ATIVO').count()
        context['entregas_pendentes'] = EntregaEPI.objects.filter(assinatura_recebimento__isnull=True).count()
        
        # Adicione aqui um KPI de EPIs próximos do vencimento, se desejar
        # context['epis_prox_vencimento'] = ...
        
        # --- Dados para Gráficos (Exemplo) ---
        # Substitua por suas queries reais de gráficos
        context['dados_grafico_json'] = json.dumps({
            'labels': ['Jan', 'Fev', 'Mar', 'Abr'],
            'data': [1, 3, 2, 5],
        })
        
        return context
