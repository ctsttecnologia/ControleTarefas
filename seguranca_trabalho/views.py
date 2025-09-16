# seguranca_trabalho/views.py

from collections import defaultdict
from datetime import timedelta
import json
import io
from multiprocessing.sharedctypes import Value
from urllib import request
from django.forms import DurationField
import pandas as pd
from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q, Count, Func
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.template.loader import render_to_string
from docx import Document
from weasyprint import HTML, default_url_fetcher
from django.views.generic.edit import FormMixin
from usuario.models import Filial
from departamento_pessoal.models import Cargo, Funcionario
from usuario.views import StaffRequiredMixin
from .forms import AssinaturaEntregaForm, EntregaEPIForm, EquipamentoForm, FabricanteForm, FichaEPIForm, FornecedorForm
from .models import EntregaEPI, Equipamento, Fabricante, FichaEPI, Fornecedor, Funcao, MatrizEPI
from django.conf import settings
from core.mixins import ViewFilialScopedMixin, FilialCreateMixin 
from django.core.exceptions import PermissionDenied
from django.db import transaction
from core.mixins import SSTPermissionMixin


# --- Ações de Entrega ---
import logging
logger = logging.getLogger(__name__)


# --- Funções e Mixins de Permissão (mantidos como no original) ---
def custom_url_fetcher(url):

    if url.startswith(settings.MEDIA_URL):
        path = (settings.MEDIA_ROOT / url[len(settings.MEDIA_URL):]).as_posix()
        return default_url_fetcher(f'file://{path}')
    return default_url_fetcher(url)

# --- CRUD de Equipamentos ---

class EquipamentoListView(ViewFilialScopedMixin, SSTPermissionMixin, ListView):
    model = Equipamento
    template_name = 'seguranca_trabalho/equipamento_list.html'
    context_object_name = 'equipamentos'
    permission_required = 'seguranca_trabalho.view_equipamento'

class EquipamentoDetailView(ViewFilialScopedMixin, SSTPermissionMixin, DetailView):
    model = Equipamento
    template_name = 'seguranca_trabalho/equipamento_detail.html'
    context_object_name = 'equipamento'
    permission_required = 'seguranca_trabalho.view_equipamento'

class EquipamentoCreateView(FilialCreateMixin, SSTPermissionMixin, CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    permission_required = 'seguranca_trabalho.add_equipamento'


class EquipamentoUpdateView(ViewFilialScopedMixin, SSTPermissionMixin, UpdateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    permission_required = 'seguranca_trabalho.change_equipamento'

    def get_queryset(self):
        # A sua lógica de otimização de consulta
        queryset = super().get_queryset().select_related('fabricante', 'fornecedor_padrao')
        return queryset

    # O método form_valid abaixo garante que a data de cadastro não seja alterada
    def form_valid(self, form):
        # A data de cadastro é auto_now_add=True, então o formulário não precisa dela.
        # Mas para outros campos que não são 'auto', a lógica a seguir não se aplica.
        # Deixe o form_valid padrão do UpdateView para persistir os dados.

        # A menos que você tenha uma lógica de negócio específica aqui
        # que esteja removendo o valor da data, você não precisa mexer.
        return super().form_valid(form)

class EquipamentoDeleteView(ViewFilialScopedMixin, SSTPermissionMixin, DeleteView):
    model = Equipamento
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    context_object_name = 'object'
    permission_required = 'seguranca_trabalho.delete_equipamento'

# --- CRUD de Fabricantes ---

class FabricanteListView(ViewFilialScopedMixin, SSTPermissionMixin, ListView):
    model = Fabricante
    template_name = 'seguranca_trabalho/fabricante_list.html'
    context_object_name = 'fabricantes'
    permission_required = 'seguranca_trabalho.view_fabricante'

class FabricanteDetailView(ViewFilialScopedMixin, SSTPermissionMixin, DetailView):
    model = Fabricante
    template_name = 'seguranca_trabalho/fabricante_detail.html'
    context_object_name = 'fabricante'
    permission_required = 'seguranca_trabalho.view_fabricante'

class FabricanteCreateView(FilialCreateMixin, SSTPermissionMixin, CreateView):
    model = Fabricante
    form_class = FabricanteForm
    template_name = 'seguranca_trabalho/fabricante_form.html'
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')
    permission_required = 'seguranca_trabalho.add_fabricante'

class FabricanteUpdateView(ViewFilialScopedMixin, SSTPermissionMixin, UpdateView):
    model = Fabricante
    form_class = FabricanteForm
    template_name = 'seguranca_trabalho/fabricante_form.html'
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')
    permission_required = 'seguranca_trabalho.change_fabricante'

# --- CRUD de Fornecedores ---

class FornecedorListView(ViewFilialScopedMixin, SSTPermissionMixin, ListView):
    model = Fornecedor
    template_name = 'seguranca_trabalho/fornecedor_list.html'
    context_object_name = 'fornecedores'
    permission_required = 'seguranca_trabalho.view_fornecedor'


class FornecedorDetailView(ViewFilialScopedMixin, SSTPermissionMixin, DetailView):
    model = Fornecedor
    template_name = 'seguranca_trabalho/fornecedor_detail.html'
    context_object_name = 'fornecedor'
    permission_required = 'seguranca_trabalho.view_fornecedor'

    def get_queryset(self):
        # Chama o queryset padrão da view
        queryset = super().get_queryset()
        
        # Adiciona a otimização com select_related para carregar o endereço
        # Isso garante que o endereço seja carregado na mesma consulta do fornecedor
        return queryset.select_related('endereco')

class FornecedorCreateView(FilialCreateMixin, SSTPermissionMixin, CreateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'seguranca_trabalho/fornecedor_form.html'
    success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')
    permission_required = 'seguranca_trabalho.add_fornecedor'

class FornecedorUpdateView(ViewFilialScopedMixin, SSTPermissionMixin, UpdateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'seguranca_trabalho/fornecedor_form.html'
    success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')
    permission_required = 'seguranca_trabalho.change_fornecedor'

# ========================================================================
# CRUD DE FICHAS DE EPI E AÇÕES
# ========================================================================

class FichaEPIListView(ViewFilialScopedMixin, SSTPermissionMixin, ListView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_list.html'
    context_object_name = 'fichas'
    paginate_by = 20
    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get_queryset(self):
        # A lógica aqui já estava correta, chamando super() primeiro.
        qs = super().get_queryset()
        qs = qs.select_related('funcionario', 'funcionario__cargo').order_by('-criado_em')
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(funcionario__nome_completo__icontains=query) |
                Q(funcionario__matricula__icontains=query)
            )
        return qs

class FichaEPICreateView(ViewFilialScopedMixin, SSTPermissionMixin, CreateView):
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_create.html'
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')
    permission_required = 'seguranca_trabalho.add_fichaepi'


    # Filtra o campo 'funcionario' para mostrar apenas os da filial ativa.
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request  # Passa o request para o form
        return kwargs

    def form_valid(self, form):
        # A filial da FichaEPI é herdada do funcionário.
        form.instance.filial = form.cleaned_data['funcionario'].filial
        messages.success(self.request, "Ficha de EPI criada com sucesso!")
        return super().form_valid(form)

# Substitua a sua FichaEPIDetailView por esta:
class FichaEPIDetailView(ViewFilialScopedMixin, SSTPermissionMixin, FormMixin, DetailView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_detail.html'
    context_object_name = 'ficha'
    form_class = EntregaEPIForm
    permission_required = 'seguranca_trabalho.view_fichaepi'    
    
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            if not request.user.has_perm('seguranca_trabalho.add_entregaepi'):
                raise PermissionDenied("Você não tem permissão para registrar uma nova entrega.")
        else: # GET e outros métodos
            if not request.user.has_perm('seguranca_trabalho.view_fichaepi'):
                 raise PermissionDenied("Você não tem permissão para visualizar esta ficha.")
        return super().dispatch(request, *args, **kwargs)


    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        # Adiciona o formulário e a lista de entregas ao contexto do template
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['entregas'] = EntregaEPI.objects.filter(ficha=self.object).select_related('equipamento').order_by('-data_entrega')
        return context

    def post(self, request, *args, **kwargs):
        """
        Este método é chamado quando o formulário é enviado (POST).
        """
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        """
        Cria o objeto mas não o salva no banco ainda (commit=False),
        permite que o modifiquemos antes de salvar.
        """
        nova_entrega = form.save(commit=False)
        # Associa a entrega à ficha de EPI que está aberta na tela
        nova_entrega.ficha = self.object
        # FINALMENTE, DEFINE A DATA DE ENTREGA.
        nova_entrega.data_entrega = timezone.now().date()
        # Agora salva o objeto completo no banco de dados
        nova_entrega.filial = self.object.filial
        nova_entrega.save()
        messages.success(self.request, "Nova entrega de EPI registrada com sucesso!")
        # Redireciona para a página de sucesso
        return redirect(self.get_success_url())

class FichaEPIUpdateView(ViewFilialScopedMixin, SSTPermissionMixin, UpdateView):
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_form.html'
    permission_required = 'seguranca_trabalho.change_fichaepi'  

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})

class FichaEPIDeleteView(ViewFilialScopedMixin, SSTPermissionMixin, DeleteView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')
    context_object_name = 'object'
    permission_required = 'seguranca_trabalho.delete_fichaepi'

# --- Ações de Entrega ---
# A lógica dessas views customizadas já filtrava manualmente, o que está correto.
# Apenas garantimos que o get_object_or_404 use um queryset já filtrado.
def get_entrega_scoped(request, pk):
    """Função auxiliar para buscar uma entrega de forma segura."""
    filial_id = request.session.get('active_filial_id')
    if not filial_id:
        raise PermissionDenied("Nenhuma filial selecionada.")
    
    # O filtro é feito via Ficha, garantindo que a entrega pertence a um funcionário da filial.
    return get_object_or_404(EntregaEPI, pk=pk, ficha__filial_id=filial_id)


# 'AssinarEntregaView' 

class AssinarEntregaView(ViewFilialScopedMixin, SSTPermissionMixin, UpdateView):
    model = EntregaEPI
    form_class = AssinaturaEntregaForm
    template_name = 'seguranca_trabalho/entrega_sign.html'
    context_object_name = 'entrega'
    permission_required = 'seguranca_trabalho.assinar_entregaepi'
   
    
    def get_object(self, queryset=None):
        """Sobrescreve o método para adicionar a validação de filial."""
        pk = self.kwargs.get(self.pk_url_kwarg)
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            raise Http404("Nenhuma filial selecionada. Acesso negado.")

        obj = get_object_or_404(
            EntregaEPI,
            pk=pk,
            ficha__filial_id=filial_id
        )
        return obj

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.ficha.pk})

    def get(self, request, *args, **kwargs):
        """Validação antes de exibir o formulário GET."""
        self.object = self.get_object()
        if self.object.data_devolucao or self.object.data_assinatura:
            messages.info(request, "Esta entrega já foi processada e não pode mais ser assinada.")
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        """Processa a assinatura e salva."""
        # A lógica de salvar os dados da assinatura será feita aqui
        signature_b64 = self.request.POST.get('assinatura_base64')
        signature_image = self.request.FILES.get('assinatura_imagem')

        if not signature_b64 and not signature_image:
            messages.error(self.request, "Nenhuma assinatura foi fornecida.")
            return self.form_invalid(form)

        if signature_image:
            self.object.assinatura_imagem = signature_image
            self.object.assinatura_recebimento = None
        elif signature_b64:
            self.object.assinatura_recebimento = signature_b64
            self.object.assinatura_imagem = None

        self.object.data_assinatura = timezone.now()
        
        # Chama a função super para salvar e redirecionar
        return super().form_valid(form)

class RegistrarDevolucaoView(SSTPermissionMixin, View):

    permission_required = 'seguranca_trabalho.add_devolucao'
    """
    View refatorada para processar a devolução de um EPI de forma segura e atômica.
    - Esta view responde apenas a requisições POST.
    - O objeto 'entrega' é buscado de forma segura no método dispatch.
    - A lógica de devolução é protegida por uma transação de banco de dados.
    """
    def dispatch(self, request, *args, **kwargs):
        """
        Busca o objeto 'entrega' de forma segura antes de processar o POST.
        """
        # Garante que esta view só possa ser acessada via POST
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])

        filial_id = request.session.get('active_filial_id')
        if not filial_id:
            messages.error(request, "Nenhuma filial selecionada. Acesso negado.")
            return redirect('seguranca_trabalho:dashboard')

        try:
            pk = self.kwargs.get('pk')
            self.entrega = get_object_or_404(
                EntregaEPI,
                pk=pk,
                ficha__filial_id=filial_id
            )
        except Http404:
            messages.error(request, "A entrega de EPI não foi encontrada ou você não tem permissão para modificá-la.")
            return redirect('seguranca_trabalho:ficha_list')

        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        Executa a ação de registrar a devolução.
        """
        # Validação: Verifica se o EPI já foi devolvido para evitar ações duplicadas.
        if self.entrega.data_devolucao:
            messages.warning(request, f"O EPI '{self.entrega.equipamento.nome}' já havia sido devolvido anteriormente.")
            return redirect(reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.entrega.ficha.pk}))

        # Atualiza os campos da devolução
        self.entrega.data_devolucao = timezone.now().date()  # Salva apenas a data
        self.entrega.recebedor_devolucao = request.user      # Usuário logado que recebeu
        self.entrega.save()

        messages.success(request, f"Devolução do EPI '{self.entrega.equipamento.nome}' registrada com sucesso.")

        # Redireciona de volta para a ficha do funcionário
        return redirect(reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.entrega.ficha.pk}))

class GerarFichaPDFView(SSTPermissionMixin, View):

    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get(self, request, *args, **kwargs):
        filial_id = request.session.get('active_filial_id')
        if not filial_id:
            raise PermissionDenied("Nenhuma filial selecionada.")
        ficha = get_object_or_404(FichaEPI, pk=self.kwargs['pk'])
        entregas = EntregaEPI.objects.filter(ficha=ficha).order_by('data_entrega')
        context = {
            'ficha': ficha,
            'entregas': entregas,
            'data_emissao': timezone.now(),
        }
        html_string = render_to_string('seguranca_trabalho/ficha_pdf_template.html', context)
          # A MUDANÇA ESTÁ AQUI: adicionamos o argumento 'url_fetcher'
        html = HTML(
            string=html_string, 
            base_url=request.build_absolute_uri(),
            url_fetcher=custom_url_fetcher # Usando nosso "tradutor"
        )
        pdf = html.write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ficha_epi_{ficha.funcionario.matricula}.pdf"'
        return response    

# --- VIEW DO PAINEL ---

class DateAdd(Func):

    """
    Função customizada para usar o DATE_ADD do MySQL
    de forma segura, compondo as expressões corretamente.
    """
    function = 'DATE_ADD'
    template = '%(function)s(%(expressions)s)'

    def __init__(self, date_expression, days_expression, **extra):
        # Cria uma expressão interna para "INTERVAL 'N' DAY"
        # O Django irá compilar 'days_expression' para o nome da coluna corretamente
        interval_expression = Func(
            days_expression,
            template="INTERVAL %(expressions)s DAY"
        )
        super().__init__(date_expression, interval_expression, **extra)

class DashboardSSTView(ViewFilialScopedMixin, SSTPermissionMixin, TemplateView):

    template_name = 'seguranca_trabalho/dashboard.html'
    permission_required = 'seguranca_trabalho.view_equipamento'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # O método get_queryset já filtra pela filial, vamos usá-lo
        equipamentos_da_filial = self.get_queryset(Equipamento)
        fichas_da_filial = self.get_queryset(FichaEPI)
        entregas_da_filial = self.get_queryset(EntregaEPI)
        matriz_da_filial = self.get_queryset(MatrizEPI)

        # --- 1. DADOS PARA OS CARDS DE KPI (COM NOMES CORRIGIDOS) ---
        context['total_equipamentos_ativos'] = equipamentos_da_filial.filter(ativo=True).count()
        # O template espera 'fichas_ativas'
        context['fichas_ativas'] = fichas_da_filial.filter(funcionario__status='ATIVO').count()
        # O template espera 'entregas_pendentes_assinatura'
        context['entregas_pendentes_assinatura'] = entregas_da_filial.filter(
            data_devolucao__isnull=True, 
            data_assinatura__isnull=True # Simplificado, já que a assinatura é uma data
        ).count()

        # --- 2. CÁLCULO DE EPIs VENCENDO ---
        today = timezone.now().date()
        thirty_days_from_now = today + timedelta(days=30)
        
        entregas_ativas = entregas_da_filial.filter(
            data_devolucao__isnull=True, data_entrega__isnull=False
        ).select_related('equipamento')

        epis_vencendo_30d_count = 0
        for entrega in entregas_ativas:
            vida_util = entrega.equipamento.vida_util_dias
            if vida_util is not None:
                vencimento = entrega.data_entrega + timedelta(days=vida_util)
                if today <= vencimento <= thirty_days_from_now:
                    epis_vencendo_30d_count += 1
        
        # O template espera 'epis_vencendo_em_30_dias'
        context['epis_vencendo_em_30_dias'] = epis_vencendo_30d_count

        # --- 3. DADOS PARA OS GRÁFICOS (mantido como JSON) ---
        # Gráfico da Matriz de EPI por Função
        matriz_chart_data = matriz_da_filial.values('funcao__nome').annotate(
            num_epis=Count('equipamento')
        ).order_by('-num_epis')[:10] # Limita aos 10 maiores
        
        if matriz_chart_data:
            # CORREÇÃO: Nomes que o novo template usará
            context['matriz_labels'] = json.dumps([m['funcao__nome'] for m in matriz_chart_data])
            context['matriz_data'] = json.dumps([m['num_epis'] for m in matriz_chart_data])

        # (A lógica do outro gráfico de situação foi removida para simplificar,
        # pois o template não a usava e pode ser complexa. Focamos no que pode ser exibido.)

        context['titulo_pagina'] = "Painel de Segurança do Trabalho"
        return context

    def get_queryset(self, model):
        """
        Método auxiliar para obter o queryset filtrado de forma robusta.
        """
        active_filial_id = self.request.session.get('active_filial_id')
        
        qs = model.objects.all()

        if active_filial_id:
            if hasattr(model, 'filial'):
                return qs.filter(filial_id=active_filial_id)
            # Para modelos como FichaEPI e EntregaEPI, o filtro pode ser através do funcionário
            elif hasattr(model, 'funcionario') and hasattr(model.funcionario.field.related_model, 'filial'):
                return qs.filter(funcionario__filial_id=active_filial_id)
            return qs.none() # Se não sabe como filtrar, não mostra nada
        
        if self.request.user.is_superuser:
            return qs

        return qs.none()

class BaseExportView(LoginRequiredMixin, View):
    def get_scoped_queryset(self, model, related_fields=None):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            messages.error(self.request, "Selecione uma filial para exportar os dados.")
            return model.objects.none()

        # Lógica de filtro baseada na estrutura do modelo
        if hasattr(model, 'filial'):
            qs = model.objects.filter(filial_id=filial_id)
        elif hasattr(model, 'funcionario'):
            qs = model.objects.filter(funcionario__filial_id=filial_id)
        else:
            return model.objects.none()
        
        if related_fields:
            qs = qs.select_related(*related_fields)
        return qs

# O nome da classe deve ser EXATAMENTE este
class ControleEPIPorFuncaoView(SSTPermissionMixin, TemplateView):

    permission_required = 'seguranca_trabalho.view_fichaepi'
    template_name = 'seguranca_trabalho/controle_epi_por_funcao.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        
        active_filial_id = request.session.get('active_filial_id')

        if not active_filial_id:
            messages.warning(request, "Nenhuma filial selecionada. Por favor, escolha uma no menu superior.")
            context['titulo_pagina'] = "Matriz de EPIs"
            context['funcoes'] = []
            context['equipamentos'] = []
            return context
        
        try:
            filial_atual = Filial.objects.get(pk=active_filial_id)
        except Filial.DoesNotExist:
            messages.error(request, "A filial selecionada na sua sessão é inválida.")
            return context

        funcoes_da_filial = Funcao.objects.da_filial(filial_atual).order_by('nome')
        equipamentos_ativos = Equipamento.objects.filter(ativo=True).order_by('nome')

        matriz_data = {}
        dados_salvos = MatrizEPI.objects.filter(
            funcao__in=funcoes_da_filial
        ).select_related('funcao', 'equipamento')

        for item in dados_salvos:
            if item.funcao_id not in matriz_data:
                matriz_data[item.funcao_id] = {}
            if item.equipamento_id:
                matriz_data[item.funcao_id][item.equipamento_id] = item.frequencia_troca_meses

        context['titulo_pagina'] = f"Matriz de EPIs - {filial_atual.nome}"
        context['funcoes'] = funcoes_da_filial
        context['equipamentos'] = equipamentos_ativos
        context['matriz_data'] = matriz_data
        
        return context

    def post(self, request, *args, **kwargs):
        active_filial_id = request.session.get('active_filial_id')
        if not active_filial_id:
            messages.error(request, "Não foi possível salvar. Nenhuma filial selecionada.")
            return redirect(request.path_info)

        funcoes_da_filial = Funcao.objects.filter(filial_id=active_filial_id)
        equipamentos_ativos = Equipamento.objects.filter(ativo=True)

        for funcao in funcoes_da_filial:
            for equipamento in equipamentos_ativos:
                input_name = f'freq_{funcao.id}_{equipamento.id}'
                frequencia_str = request.POST.get(input_name)
                
                if frequencia_str and frequencia_str.isdigit() and int(frequencia_str) > 0:
                    frequencia = int(frequencia_str)
                    MatrizEPI.objects.update_or_create(
                        funcao=funcao,
                        equipamento=equipamento,
                        # Adiciona a filial ao criar/atualizar, garantindo consistência
                        filial_id=active_filial_id, 
                        defaults={'frequencia_meses': frequencia}
                    )
                else:
                    MatrizEPI.objects.filter(funcao=funcao, equipamento=equipamento).delete()
        
        messages.success(request, "Matriz de EPIs salva com sucesso!")
        return redirect(request.path_info)
       
# --- VIEWS DE EXPORTAÇÃO ---
class ExportarFuncionariosExcelView(StaffRequiredMixin, View): 
    def get(self, request, *args, **kwargs):
        # CORREÇÃO: Aplicando o filtro de filial manualmente.
        funcionarios = Funcionario.objects.for_request(request).select_related('cargo', 'departamento').all()
        

        data = [
            {
                'Matrícula': f.matricula, 'Nome Completo': f.nome_completo, 'Email Pessoal': f.email_pessoal,
                'Telefone': f.telefone, 'Cargo': f.cargo.nome if f.cargo else '-',
                'Departamento': f.departamento.nome if f.departamento else '-',
                'Data de Admissão': f.data_admissao.strftime('%d/%m/%Y') if f.data_admissao else '-',
                'Salário': f.salario, 'Status': f.get_status_display(),
            } for f in funcionarios
        ]
        df = pd.DataFrame(data)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.xlsx"'
        df.to_excel(response, index=False)
        return response
    
class RelatorioSSTPDFView(SSTPermissionMixin, View):

    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get(self, request, *args, **kwargs):
        context = {
            'data_emissao': timezone.now(),
            'entregas': EntregaEPI.objects.select_related('ficha__funcionario', 'equipamento').all(),
        }
        html_string = render_to_string('seguranca_trabalho/relatorio_geral_pdf.html', context)
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf = html.write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_sst.pdf"'
        return response
    
class ExportarFuncionariosPDFView(StaffRequiredMixin, View): 

    def get(self, request, *args, **kwargs):
        
        funcionarios = Funcionario.objects.for_request(request).select_related('cargo', 'departamento').filter(status='ATIVO')

        context = {
            'funcionarios': funcionarios,
            'data_emissao': timezone.now().strftime('%d/%m/%Y às %H:%M'),
            'nome_filial': request.user.filial.nome if hasattr(request.user, 'filial') else 'Geral'
        }
        html_string = render_to_string('departamento_pessoal/relatorio_funcionarios_pdf.html', context)
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf_file = html.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.pdf"'
        return response
    
class ExportarFuncionariosWordView(StaffRequiredMixin, View): 

    def get(self, request, *args, **kwargs):
      
        funcionarios = Funcionario.objects.for_request(request).select_related('cargo', 'departamento').filter(status='ATIVO')

        document = Document()
        document.add_heading('Relatório de Colaboradores', level=1)
        data_emissao = timezone.now().strftime('%d/%m/%Y às %H:%M')
        document.add_paragraph(f'Relatório gerado em: {data_emissao}', style='Caption')
        document.add_paragraph()

        table = document.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text, hdr_cells[1].text, hdr_cells[2].text, hdr_cells[3].text = 'Nome Completo', 'Cargo', 'Departamento', 'Data de Admissão'

        for f in funcionarios:
            row_cells = table.add_row().cells
            row_cells[0].text = f.nome_completo
            row_cells[1].text = f.cargo.nome if f.cargo else '-'
            row_cells[2].text = f.departamento.nome if f.departamento else '-'
            row_cells[3].text = f.data_admissao.strftime('%d/%m/%Y') if f.data_admissao else '-'

        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.docx"'
        return response
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text, hdr_cells[1].text, hdr_cells[2].text, hdr_cells[3].text = 'Nome Completo', 'Cargo', 'Departamento', 'Data de Admissão'

        for f in funcionarios:
            row_cells = table.add_row().cells
            row_cells[0].text = f.nome_completo
            row_cells[1].text = f.cargo.nome if f.cargo else '-'
            row_cells[2].text = f.departamento.nome if f.departamento else '-'
            row_cells[3].text = f.data_admissao.strftime('%d/%m/%Y') if f.data_admissao else '-'

        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.docx"'
        return response
    

