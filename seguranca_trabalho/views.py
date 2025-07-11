# seguranca_trabalho/views.py

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
from django.db.models import Count, Q

from .models import (
    Equipamento, FichaEPI, EntregaEPI, Fabricante, Fornecedor, Funcao, 
    MatrizEPI, MovimentacaoEstoque
)
from .forms import (
    EquipamentoForm, FichaEPIForm, EntregaEPIForm, AssinaturaForm, 
    FabricanteForm, FornecedorForm
)
from departamento_pessoal.models import Funcionario
from tarefas.models import Tarefas # Supondo que você queira manter isso no dashboard

# --- MIXINS E CLASSES BASE ---

class SSTPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Mixin para verificar se o usuário tem permissão para acessar a área de SST.
    Altere a permissão para uma mais específica do seu app.
    """
    permission_required = 'auth.view_user' # Ex: 'seguranca_trabalho.view_equipamento'
    
    def handle_no_permission(self):
        messages.error(self.request, "Você não tem permissão para acessar esta página.")
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

# --- VIEWS DO DASHBOARD ---

class DashboardSSTView(SSTPermissionMixin, TemplateView):
    template_name = 'seguranca_trabalho/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Dashboard de Segurança do Trabalho'
        
        # KPIs de SST
        trinta_dias_frente = timezone.now() + timezone.timedelta(days=30)
        entregas_ativas = EntregaEPI.objects.filter(data_devolucao__isnull=True, assinatura_recebimento__isnull=False)
        
        context['total_equipamentos_ativos'] = Equipamento.objects.filter(ativo=True).count()
        context['fichas_ativas'] = FichaEPI.objects.filter(funcionario__status='ATIVO').count()
        context['entregas_pendentes_assinatura'] = EntregaEPI.objects.filter(assinatura_recebimento__isnull=True).count()
        context['epis_vencendo_em_30_dias'] = sum(1 for e in entregas_ativas if e.data_vencimento_uso and e.data_vencimento_uso <= trinta_dias_frente)
        
        # Outras métricas (ex: de Tarefas, se aplicável)
        if 'tarefas' in settings.INSTALLED_APPS:
            tarefas_sst = Tarefas.objects.filter(responsavel=self.request.user) # Adicionar filtro por categoria, se houver
            context['tarefas_pendentes_usuario'] = tarefas_sst.filter(status__in=['pendente', 'andamento']).count()
        
        return context

# --- CRUDs DE CATÁLOGO (Equipamento, Fabricante, Fornecedor) ---

# Fabricante
class FabricanteListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = Fabricante
    template_name = 'seguranca_trabalho/catalogo/fabricante_list.html'

class FabricanteDetailView(SSTPermissionMixin, DetailView):
    model = Fabricante
    template_name = 'seguranca_trabalho/catalogo/fabricante_detail.html'

class FabricanteCreateView(SSTPermissionMixin, SuccessMessageMixin, CreateView):
    model = Fabricante
    form_class = FabricanteForm
    template_name = 'seguranca_trabalho/catalogo/fabricante_form.html'
    success_message = "Fabricante cadastrado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')

class FabricanteUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Fabricante
    form_class = FabricanteForm
    template_name = 'seguranca_trabalho/catalogo/fabricante_form.html'
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
    template_name = 'seguranca_trabalho/catalogo/fornecedor_list.html'

class FornecedorDetailView(SSTPermissionMixin, DetailView):
    model = Fornecedor
    template_name = 'seguranca_trabalho/catalogo/fornecedor_detail.html'

class FornecedorCreateView(SSTPermissionMixin, SuccessMessageMixin, CreateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'seguranca_trabalho/catalogo/fornecedor_form.html'
    success_message = "Fornecedor cadastrado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')

class FornecedorUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'seguranca_trabalho/catalogo/fornecedor_form.html'
    success_message = "Fornecedor atualizado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')
    
# Equipamento
class EquipamentoListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = Equipamento
    queryset = Equipamento.objects.select_related('fabricante').filter(ativo=True)
    template_name = 'seguranca_trabalho/catalogo/equipamento_list.html'
    context_object_name = 'equipamentos'

class EquipamentoDetailView(SSTPermissionMixin, DetailView):
    model = Equipamento
    queryset = Equipamento.objects.select_related('fabricante', 'fornecedor_padrao')
    template_name = 'seguranca_trabalho/catalogo/equipamento_detail.html'

class EquipamentoCreateView(SSTPermissionMixin, SuccessMessageMixin, CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/catalogo/equipamento_form.html'
    success_message = "Equipamento cadastrado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')

class EquipamentoUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/catalogo/equipamento_form.html'
    success_message = "Equipamento atualizado com sucesso!"
    
    def get_success_url(self):
        return reverse('seguranca_trabalho:equipamento_detail', kwargs={'pk': self.object.pk})

class EquipamentoDeleteView(SSTPermissionMixin, SuccessDeleteMessageMixin, DeleteView):
    model = Equipamento
    template_name = 'seguranca_trabalho/confirm_delete.html' # Um template genérico de confirmação
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    success_message = "Equipamento excluído com sucesso."


# --- CRUD DE FICHAS DE EPI E ENTREGAS ---

class FichaEPIListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_list.html'
    context_object_name = 'fichas'
    queryset = FichaEPI.objects.select_related('funcionario__cargo').filter(funcionario__status='ATIVO')

class FichaEPICreateView(SSTPermissionMixin, CreateView):
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_create.html'
    
    def form_valid(self, form):
        try:
            # Garante que o usuário do request seja o criador (se houver campo)
            # form.instance.criado_por = self.request.user 
            self.object = form.save()
            messages.success(self.request, f"Ficha de EPI para {self.object.funcionario.nome_completo} criada com sucesso!")
            return redirect(self.get_success_url())
        except IntegrityError:
            messages.error(self.request, "Este funcionário já possui uma ficha de EPI.")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})

class FichaEPIDetailView(SSTPermissionMixin, DetailView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_detail.html'
    context_object_name = 'ficha'
    
    def get_queryset(self):
        # Otimiza a query para buscar dados relacionados de uma só vez
        return FichaEPI.objects.select_related('funcionario__cargo', 'funcao').prefetch_related(
            'entregas__equipamento'
        ).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entrega_form'] = EntregaEPIForm()
        context['assinatura_form'] = AssinaturaForm()
        return context


# --- VIEWS DE AÇÃO (Entregas, Assinaturas, Devoluções) ---

class AdicionarEntregaView(SSTPermissionMixin, View):

    @transaction.atomic
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
                quantidade=-entrega.quantidade,
                responsavel=request.user,
                justificativa=f"Entrega para {ficha.funcionario.nome_completo}",
                entrega_associada=entrega
            )
            
            messages.success(request, "Entrega registrada com sucesso. Aguardando assinatura do colaborador.")
        else:
            # Concatena os erros do formulário em uma única mensagem
            error_list = [f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()]
            error_message = "Erro ao registrar entrega. " + " ".join(error_list)
            messages.error(request, error_message)
            
        return redirect('seguranca_trabalho:ficha_detalhe', pk=ficha.pk)

class AssinarEntregaView(SSTPermissionMixin, View):

    def post(self, request, *args, **kwargs):
        entrega = get_object_or_404(EntregaEPI, pk=kwargs.get('pk'), assinatura_recebimento__isnull=True)
        form = AssinaturaForm(request.POST)

        if form.is_valid():
            entrega.assinatura_recebimento = form.cleaned_data['assinatura_base64']
            entrega.data_entrega = timezone.now()
            entrega.save(update_fields=['assinatura_recebimento', 'data_entrega'])
            messages.success(request, "Recebimento de EPI assinado com sucesso!")
        else:
            messages.error(request, "Erro no formulário de assinatura.")
        
        return redirect('seguranca_trabalho:ficha_detalhe', pk=entrega.ficha.pk)

class RegistrarDevolucaoView(SSTPermissionMixin, View):
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        entrega = get_object_or_404(EntregaEPI, pk=kwargs.get('pk'), data_devolucao__isnull=True)
        
        entrega.data_devolucao = timezone.now()
        entrega.save(update_fields=['data_devolucao'])
        
        # Opcional: Lógica para retornar o item ao estoque, se for reutilizável
        # MovimentacaoEstoque.objects.create(...)
        
        messages.success(request, "Devolução de EPI registrada com sucesso!")
        return redirect('seguranca_trabalho:ficha_detalhe', pk=entrega.ficha.pk)
    
    
