
# departamento_pessoal/views.py

# --- Imports Corrigidos ---
from collections import defaultdict
import json
import io
from multiprocessing.sharedctypes import Value
from django.forms import DurationField
import pandas as pd
from django.http import HttpResponse
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q, Count, ExpressionWrapper, DateField, Func, F, DurationField
from django.db.models.functions import Coalesce, Cast
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.template.loader import render_to_string
# Defina o SSTPermissionMixin caso não exista (ajuste conforme sua regra de permissão)
from django.contrib.auth.mixins import PermissionRequiredMixin
from docx import Document
from weasyprint import HTML
from datetime import timedelta
from django.views.generic.edit import FormMixin
#Import explícito dos modelos e forms.
from departamento_pessoal.models import Funcionario, Departamento, Cargo, Documento
from departamento_pessoal.forms import AdmissaoForm, FuncionarioForm, DepartamentoForm, CargoForm, DocumentoForm
from seguranca_trabalho.forms import EntregaEPIForm, EquipamentoForm, FabricanteForm, FichaEPIForm, FornecedorForm
from seguranca_trabalho.models import EntregaEPI, Equipamento, Fabricante, FichaEPI, Fornecedor, MatrizEPI
from django.conf import settings
from weasyprint import default_url_fetcher # Importe o default_url_fetcher
from core.mixins import FilialScopedQuerysetMixin
import logging




logger = logging.getLogger(__name__)

# Adicione esta função no topo do seu arquivo de views
def custom_url_fetcher(url):
    """
    "Traduz" URLs de mídia (/media/...) para caminhos de arquivo locais (file://...)
    que a WeasyPrint possa entender.
    """
    if url.startswith(settings.MEDIA_URL):
        # Converte a URL para um caminho de arquivo no disco
        path = (settings.MEDIA_ROOT / url[len(settings.MEDIA_URL):]).as_posix()
        # Passa o caminho de arquivo local para o fetcher padrão da WeasyPrint
        return default_url_fetcher(f'file://{path}')
    # Para todas as outras URLs (http, https, etc.), usa o comportamento padrão
    return default_url_fetcher(url)

    
class StaffRequiredMixin(PermissionRequiredMixin):
    """
    Mixin que garante que o usuário tem uma permissão específica para acessar as views.
    MELHORIA: A permissão pode ser sobrescrita em cada view para ser mais granular.
    """
    permission_required = 'auth.view_user'  # Permissão genérica, ajuste se necessário
    raise_exception = True

class SSTPermissionMixin(PermissionRequiredMixin):
    """
    Garante que o usuário tem permissão para acessar o módulo de SST.
    Ajuste a permissão conforme o seu sistema de grupos e permissões.
    """
    permission_required = 'seguranca_trabalho.view_equipamento' # Exemplo de permissão
    raise_exception = True

# --- VIEWS PARA FUNCIONÁRIOS ---

class FuncionarioListView(FilialScopedQuerysetMixin, StaffRequiredMixin, ListView):
    model = Funcionario
    template_name = 'departamento_pessoal/lista_funcionarios.html'
    context_object_name = 'funcionarios'
    paginate_by = 15

    def get_queryset(self):
        # A otimização e a busca continuam corretas.
        queryset = super().get_queryset().select_related('cargo', 'departamento').order_by('nome_completo')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(nome_completo__icontains=query) |
                Q(matricula__icontains=query) |
                Q(cargo__nome__icontains=query)
            )
        return queryset

class FuncionarioDetailView(FilialScopedQuerysetMixin, StaffRequiredMixin, DetailView):
    model = Funcionario
    template_name = 'departamento_pessoal/detalhe_funcionario.html'
    context_object_name = 'funcionario'

    def get_queryset(self):
        return super().get_queryset().select_related('usuario', 'cargo', 'departamento')


class FuncionarioCreateView(FilialScopedQuerysetMixin, CreateView): # CORREÇÃO: Removido FilialScopedMixin inútil
    model = Funcionario
    form_class = FuncionarioForm
    template_name = 'departamento_pessoal/funcionario_form.html'

    # MELHORIA: Lógica de associação à filial (se existir no form) deve ir aqui
    def form_valid(self, form):
        # Exemplo: Se o funcionário deve ser associado à filial do usuário que o cadastra
        # form.instance.filial = self.request.user.filial
        messages.success(self.request, "Funcionário cadastrado com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = "Cadastrar Novo Funcionário"
        return context

class FuncionarioUpdateView(FilialScopedQuerysetMixin, StaffRequiredMixin, UpdateView): # CORREÇÃO: Adicionado FilialScopedMixin
    model = Funcionario
    form_class = FuncionarioForm
    template_name = 'departamento_pessoal/funcionario_form.html'

    def form_valid(self, form):
        messages.success(self.request, "Dados do funcionário atualizados com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar: {self.object.nome_completo}"
        return context

class FuncionarioDeleteView(FilialScopedQuerysetMixin, StaffRequiredMixin, DetailView):
    model = Funcionario
    template_name = 'departamento_pessoal/confirm_delete.html'
    context_object_name = 'funcionario'

    def post(self, request, *args, **kwargs):
        funcionario = self.get_object()
        action = request.POST.get('action')

        if action == 'inativar':
            funcionario.status = 'INATIVO'
            funcionario.save()
            messages.warning(request, f"O funcionário '{funcionario.nome_completo}' foi INATIVADO.")
        elif action == 'excluir':
            nome_completo = funcionario.nome_completo
            funcionario.delete()
            messages.error(request, f"O funcionário '{nome_completo}' foi EXCLUÍDO PERMANENTEMENTE.")

        return redirect('departamento_pessoal:lista_funcionarios')

# --- VIEWS PARA O PROCESSO DE ADMISSÃO ---

class FuncionarioAdmissaoView(FilialScopedQuerysetMixin, StaffRequiredMixin, UpdateView):
    model = Funcionario
    form_class = AdmissaoForm
    template_name = 'departamento_pessoal/admissao_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Dados de admissão de '{self.object.nome_completo}' salvos com sucesso!")
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.data_admissao:
            context['titulo_pagina'] = f"Editar Admissão de {self.object.nome_completo}"
        else:
            context['titulo_pagina'] = f"Registrar Admissão para {self.object.nome_completo}"
        return context

# --- VIEWS PARA DEPARTAMENTO ---
class DepartamentoListView(FilialScopedQuerysetMixin, StaffRequiredMixin, ListView):
    model = Departamento
    template_name = 'departamento_pessoal/lista_departamento.html'
    context_object_name = 'departamentos'

class DepartamentoCreateView(FilialScopedQuerysetMixin, StaffRequiredMixin, CreateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'departamento_pessoal/departamento_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_departamento')
    extra_context = {'titulo_pagina': 'Novo Departamento'}

    def form_valid(self, form):
        messages.success(self.request, "Departamento criado com sucesso.")
        return super().form_valid(form)


class DepartamentoUpdateView(FilialScopedQuerysetMixin, StaffRequiredMixin, UpdateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'departamento_pessoal/departamento_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_departamento')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Departamento: {self.object.nome}"
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Departamento atualizado com sucesso.")
        return super().form_valid(form)


# --- VIEWS PARA CARGOS ---
class CargoListView(FilialScopedQuerysetMixin, StaffRequiredMixin, ListView):
    model = Cargo
    template_name = 'departamento_pessoal/lista_cargo.html'
    context_object_name = 'cargos'

class CargoCreateView(FilialScopedQuerysetMixin, StaffRequiredMixin, CreateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'departamento_pessoal/cargo_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_cargo')
    extra_context = {'titulo_pagina': 'Novo Cargo'}

    def form_valid(self, form):
        messages.success(self.request, "Cargo criado com sucesso.")
        return super().form_valid(form)

class CargoUpdateView(FilialScopedQuerysetMixin, StaffRequiredMixin, UpdateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'departamento_pessoal/cargo_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_cargo')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Cargo: {self.object.nome}"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Cargo atualizado com sucesso.")
        return super().form_valid(form)


# --- VIEWS PARA DOCUMENTOS (ADICIONADAS) ---

class DocumentoListView(FilialScopedQuerysetMixin, StaffRequiredMixin, ListView):
    model = Documento
    template_name = 'departamento_pessoal/lista_documentos.html'
    context_object_name = 'documentos'
    paginate_by = 10

    # CORREÇÃO: Removido método get_initial que não tem efeito em ListView
    
    def get_queryset(self):
        # Usa o queryset filtrado pela filial do mixin
        queryset = super().get_queryset().select_related('funcionario').order_by('funcionario__nome_completo', 'tipo')
        tipo_query = self.request.GET.get('tipo')
        if tipo_query:
            queryset = queryset.filter(tipo=tipo_query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos_documento'] = Documento.TIPO_CHOICES
        return context

# departamento_pessoal/views.py

class DocumentoCreateView(StaffRequiredMixin, CreateView): # CORREÇÃO: Removido FilialScopedMixin
    model = Documento
    form_class = DocumentoForm
    template_name = 'departamento_pessoal/documento_form.html'

    # CORREÇÃO: Unificado os dois métodos 'form_valid' em um só, que é o correto.
    def form_valid(self, form):
        # A view deve receber o pk do funcionário pela URL.
        funcionario_pk = self.kwargs.get('funcionario_pk')
        if not funcionario_pk:
             messages.error(self.request, "Funcionário não especificado.")
             return redirect('departamento_pessoal:lista_funcionarios') # ou outra página de erro

        # Valida se o usuário tem permissão para acessar este funcionário
        funcionario = get_object_or_404(Funcionario.objects.for_request(self.request), pk=funcionario_pk)
        
        form.instance.funcionario = funcionario
        messages.success(self.request, f"Documento adicionado com sucesso para {funcionario.nome_completo}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.kwargs['funcionario_pk']})


class DocumentoUpdateView(FilialScopedQuerysetMixin, StaffRequiredMixin, UpdateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'departamento_pessoal/documento_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_documentos')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar Documento de {self.object.funcionario.nome_completo}'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Documento atualizado com sucesso.")
        return super().form_valid(form)
    
# ========================================================================
# CRUD DE CATÁLOGOS (Equipamentos, Fabricantes, Fornecedores)
# ========================================================================


class SSTPermissionMixin(PermissionRequiredMixin):
    permission_required = 'seguranca_trabalho.view_equipamento'  # Ajuste conforme necessário
    raise_exception = True

# --- CRUD de Equipamentos ---
class EquipamentoListView(FilialScopedQuerysetMixin, SSTPermissionMixin, ListView):
    model = Equipamento
    template_name = 'seguranca_trabalho/equipamento_list.html'
    context_object_name = 'equipamentos'

class EquipamentoDetailView(SSTPermissionMixin, DetailView):
    model = Equipamento
    template_name = 'seguranca_trabalho/equipamento_detail.html'
    context_object_name = 'equipamento'

class EquipamentoCreateView(SSTPermissionMixin, CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')

class EquipamentoUpdateView(SSTPermissionMixin, UpdateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')

class EquipamentoDeleteView(SSTPermissionMixin, DeleteView):
    model = Equipamento
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')

# --- CRUD de Fabricantes ---
class FabricanteListView(SSTPermissionMixin, ListView):
    model = Fabricante
    template_name = 'seguranca_trabalho/fabricante_list.html'
    context_object_name = 'fabricantes'

class FabricanteDetailView(SSTPermissionMixin, DetailView):
    model = Fabricante
    template_name = 'seguranca_trabalho/fabricante_detail.html'
    context_object_name = 'fabricante'

class FabricanteCreateView(SSTPermissionMixin, CreateView):
    model = Fabricante
    form_class = FabricanteForm
    template_name = 'seguranca_trabalho/fabricante_form.html'
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')

class FabricanteUpdateView(SSTPermissionMixin, UpdateView):
    model = Fabricante
    form_class = FabricanteForm
    template_name = 'seguranca_trabalho/fabricante_form.html'
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')

# --- CRUD de Fornecedores ---
class FornecedorListView(SSTPermissionMixin, ListView):
    model = Fornecedor
    template_name = 'seguranca_trabalho/fornecedor_list.html'
    context_object_name = 'fornecedores'

class FornecedorDetailView(SSTPermissionMixin, DetailView):
    model = Fornecedor
    template_name = 'seguranca_trabalho/fornecedor_detail.html'
    context_object_name = 'fornecedor'

class FornecedorCreateView(SSTPermissionMixin, CreateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'seguranca_trabalho/fornecedor_form.html'
    success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')

class FornecedorUpdateView(SSTPermissionMixin, UpdateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'seguranca_trabalho/fornecedor_form.html'
    success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')

# ========================================================================
# CRUD DE FICHAS DE EPI E AÇÕES
# ========================================================================

class FichaEPIListView(FilialScopedQuerysetMixin, SSTPermissionMixin, ListView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_list.html'
    context_object_name = 'fichas'
    paginate_by = 20

    # CORREÇÃO APLICADA AQUI
    def get_queryset(self):
        """
        Corrige a consulta para respeitar o FilialScopedMixin, garantindo
        que apenas as fichas da filial do usuário sejam exibidas.
        """
        # 1. Inicia com a queryset filtrada pelo mixin (essencial!)
        qs = super().get_queryset()
        
        # 2. Adiciona otimizações e ordenação. A ordenação por '-criado_em'
        #    corresponde ao que é exibido na imagem ("Ficha Criada em").
        qs = qs.select_related('funcionario', 'funcionario__cargo').order_by('-criado_em')

        # 3. Aplica o filtro de busca sobre a queryset já filtrada.
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(funcionario__nome_completo__icontains=query) |
                Q(funcionario__matricula__icontains=query)
            )
        return qs


class FichaEPICreateView(SSTPermissionMixin, CreateView):
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_form.html'
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')

    def form_valid(self, form):
        messages.success(self.request, "Ficha de EPI criada com sucesso!")
        return super().form_valid(form)

# Substitua a sua FichaEPIDetailView por esta:
class FichaEPIDetailView(SSTPermissionMixin, FormMixin, DetailView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_detail.html'
    context_object_name = 'ficha'
    form_class = EntregaEPIForm # Especifica o formulário que esta view vai usar

    def get_success_url(self):
        # Após o sucesso, volta para a mesma página de detalhes
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
        
        # FINALMENTE, DEFINE A DATA DE ENTREGA. ESTA É A CORREÇÃO PRINCIPAL.
        nova_entrega.data_entrega = timezone.now().date()
        
        # Agora salva o objeto completo no banco de dados
        nova_entrega.save()

        messages.success(self.request, "Nova entrega de EPI registrada com sucesso!")
        
        # Redireciona para a página de sucesso
        return redirect(self.get_success_url())


class FichaEPIUpdateView(SSTPermissionMixin, UpdateView):
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_form.html'

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})

class FichaEPIDeleteView(SSTPermissionMixin, DeleteView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')
    context_object_name = 'object' # Nome genérico para o template

# --- Ações de Entrega ---

class AdicionarEntregaView(SSTPermissionMixin, CreateView):
    model = EntregaEPI
    form_class = EntregaEPIForm
    template_name = 'seguranca_trabalho/entrega_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ficha'] = get_object_or_404(FichaEPI, pk=self.kwargs['ficha_pk'])
        return context

    def form_valid(self, form):
        ficha = get_object_or_404(FichaEPI, pk=self.kwargs['ficha_pk'])
        form.instance.ficha = ficha
        messages.success(self.request, f"Entrega adicionada para {ficha.funcionario.nome_completo}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.kwargs['ficha_pk']})

import logging
logger = logging.getLogger(__name__)

# SUBSTITUA A CLASSE ANTIGA 'AssinarEntregaView' POR ESTA:
class AssinarEntregaView(SSTPermissionMixin, View):
    """
    View customizada para lidar com a captura e salvamento de assinaturas.
    Ela aplica o filtro de filial manualmente para garantir a segurança.
    """
    template_name = 'seguranca_trabalho/entrega_sign.html'

    def get(self, request, *args, **kwargs):
        """
        Método GET: Exibe a página para assinar, mas apenas se a entrega
        pertencer à filial do usuário.
        """
        # CORREÇÃO DE SEGURANÇA: Usando o manager 'for_request' para filtrar por filial.
        entrega = get_object_or_404(EntregaEPI.objects.for_request(request), pk=self.kwargs.get('pk'))
        
        # ... (as validações de 'já devolvido' ou 'já assinado' continuam as mesmas)
        if entrega.data_devolucao:
            messages.warning(request, "Este EPI já foi devolvido e não pode ser assinado.")
            return redirect(reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': entrega.ficha.pk}))
        if entrega.data_assinatura:
            messages.info(request, "Esta entrega já foi assinada anteriormente.")
            return redirect(reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': entrega.ficha.pk}))

        context = {
            'entrega': entrega,
            'titulo_pagina': f"Assinar Recebimento: {entrega.equipamento.nome}"
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        entrega = get_object_or_404(EntregaEPI.objects.for_request(request), pk=self.kwargs.get('pk'))

        signature_data_text = request.POST.get('assinatura_base64')
        signature_data_image = request.FILES.get('assinatura_imagem')

        if not signature_data_text and not signature_data_image:
            messages.error(request, "Nenhuma assinatura foi fornecida. O formulário foi enviado vazio.")
            return redirect(reverse('seguranca_trabalho:assinar_entrega', kwargs={'pk': entrega.pk}))

        try:
            if signature_data_image:
                print("Salvando assinatura da IMAGEM...")
                entrega.assinatura_imagem = signature_data_image
                entrega.assinatura_recebimento = None # Limpa o outro campo
            elif signature_data_text:
                print("Salvando assinatura do DESENHO (texto)...")
                entrega.assinatura_recebimento = signature_data_text
                entrega.assinatura_imagem = None # Limpa o outro campo

            entrega.data_assinatura = timezone.now()
            entrega.save()
            
        except Exception as e:
            messages.error(request, f"Ocorreu um erro inesperado ao salvar a assinatura. Contate o suporte. (Erro: {e})")
            return redirect(reverse('seguranca_trabalho:assinar_entrega', kwargs={'pk': entrega.pk}))

        return redirect(reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': entrega.ficha.pk}))


class RegistrarDevolucaoView(SSTPermissionMixin, View):
    """
    Processa a devolução de um EPI com um clique.
    Esta view não exibe uma página (não tem método GET), ela apenas executa uma ação (método POST).
    """
    def post(self, request, *args, **kwargs):
        # Busca a entrega de EPI específica usando a chave primária (pk) da URL
        entrega_epi = get_object_or_404(EntregaEPI, pk=self.kwargs.get('pk'))

        # Atualiza os campos da devolução conforme o seu modelo
        entrega_epi.data_devolucao = timezone.now().date()  # Define a data atual
        entrega_epi.recebedor_devolucao = request.user      # Define o usuário logado como recebedor
        entrega_epi.save()

        # Adiciona uma mensagem de sucesso para o usuário
        messages.success(request, f"Devolução do EPI '{entrega_epi.equipamento.nome}' registrada com sucesso.")

        # Redireciona o usuário de volta para a página de detalhes da ficha de onde ele veio
        return redirect(reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': entrega_epi.ficha.pk}))

class GerarFichaPDFView(SSTPermissionMixin, View):
    def get(self, request, *args, **kwargs):
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
    Função customizada e corrigida para usar o DATE_ADD do MySQL
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

class DashboardSSTView(FilialScopedQuerysetMixin, SSTPermissionMixin, TemplateView):
    template_name = 'seguranca_trabalho/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Querysets base já filtrados
        equipamentos_da_filial = self.get_queryset(Equipamento)
        fichas_da_filial = self.get_queryset(FichaEPI)
        entregas_da_filial = self.get_queryset(EntregaEPI)
        matriz_da_filial = self.get_queryset(MatrizEPI)

        # --- 1. DADOS PARA OS CARDS DE KPI ---
        context['total_equipamentos_ativos'] = equipamentos_da_filial.filter(ativo=True).count()
        context['total_fichas_ativas'] = fichas_da_filial.filter(funcionario__status='ATIVO').count()
        context['total_entregas_pendentes'] = entregas_da_filial.filter(
            data_devolucao__isnull=True, 
            assinatura_recebimento__isnull=True, 
            assinatura_imagem__isnull=True
        ).count()

        # --- 2. CÁLCULO DE STATUS EM PYTHON ---
        today = timezone.now().date()
        thirty_days_from_now = today + timedelta(days=30)
        
        # Otimiza a query para buscar dados relacionados de uma só vez
        entregas_ativas = entregas_da_filial.filter(
            data_devolucao__isnull=True, data_entrega__isnull=False
        ).select_related('equipamento')

        # Inicializa contadores e estrutura para o gráfico
        epis_vencendo_30d_count = 0
        chart_data = defaultdict(lambda: {'total': 0, 'pendente': 0, 'vencido': 0})

        for entrega in entregas_ativas:
            nome_equipamento = entrega.equipamento.nome
            chart_data[nome_equipamento]['total'] += 1

            # Verifica pendência de assinatura
            if entrega.assinatura_recebimento is None and entrega.assinatura_imagem is None:
                chart_data[nome_equipamento]['pendente'] += 1

            # Calcula vencimento
            vida_util = entrega.equipamento.vida_util_dias
            if vida_util is not None:
                vencimento = entrega.data_entrega + timedelta(days=vida_util)
                
                if vencimento < today:
                    chart_data[nome_equipamento]['vencido'] += 1
                elif today <= vencimento <= thirty_days_from_now:
                    epis_vencendo_30d_count += 1
        
        context['total_epis_vencendo_30d'] = epis_vencendo_30d_count

        # --- 3. DADOS PARA OS GRÁFICOS ---
        
        # Ordena os dados do gráfico pelo total e pega os 10 maiores
        sorted_chart_data = sorted(chart_data.items(), key=lambda item: item[1]['total'], reverse=True)[:10]

        if sorted_chart_data:
            labels = [item[0] for item in sorted_chart_data]
            pendentes = [item[1]['pendente'] for item in sorted_chart_data]
            vencidos = [item[1]['vencido'] for item in sorted_chart_data]
            ativos = [item[1]['total'] - item[1]['pendente'] - item[1]['vencido'] for item in sorted_chart_data]

            context['situacao_labels'] = json.dumps(labels)
            context['situacao_data_ativo'] = json.dumps([max(0, a) for a in ativos])
            context['situacao_data_pendente'] = json.dumps(pendentes)
            context['situacao_data_vencido'] = json.dumps(vencidos)

        # Gráfico da Matriz de EPI por Função
        matriz_chart_data = matriz_da_filial.values('funcao__nome').annotate(
            num_epis=Count('equipamento')
        ).order_by('-num_epis')
        
        if matriz_chart_data:
            context['matriz_labels'] = json.dumps([m['funcao__nome'] for m in matriz_chart_data])
            context['matriz_data'] = json.dumps([m['num_epis'] for m in matriz_chart_data])

        context['titulo_pagina'] = "Painel de Segurança do Trabalho"
        return context

    def get_queryset(self, model):
        """
        Método auxiliar para obter o queryset filtrado de forma robusta.
        """
        active_filial_id = self.request.session.get('active_filial_id')
        
        if active_filial_id:
            if hasattr(model, 'filial'):
                return model.objects.filter(filial_id=active_filial_id)
            elif hasattr(model, 'funcionario'):
                return model.objects.filter(funcionario__filial_id=active_filial_id)
            return model.objects.none()
        
        if self.request.user.is_superuser:
            return model.objects.all()

        return model.objects.none()

    
# O nome da classe deve ser EXATAMENTE este
class ControleEPIPorFuncaoView(SSTPermissionMixin, TemplateView):
    template_name = 'seguranca_trabalho/controle_epi_por_funcao.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = "Controle de EPI por Função"
        # Esta é uma lógica mais complexa. Um exemplo seria:
        # 1. Buscar todos os cargos.
        # 2. Para cada cargo, buscar os EPIs recomendados (isso exigiria um M2M no modelo Cargo ou Equipamento).
        # 3. Listar os funcionários de cada cargo e verificar se possuem os EPIs.
        context['cargos'] = Cargo.objects.prefetch_related('funcionarios').all() # Exemplo
        return context
       
# --- VIEWS DE EXPORTAÇÃO ---
class ExportarFuncionariosExcelView(StaffRequiredMixin, View): # CORREÇÃO: Mixin de filial não funciona aqui
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
    
class ExportarFuncionariosPDFView(StaffRequiredMixin, View): # CORREÇÃO: Mixin de filial não funciona aqui
    def get(self, request, *args, **kwargs):
        # CORREÇÃO: Aplicando o filtro de filial manualmente.
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
    
class ExportarFuncionariosWordView(StaffRequiredMixin, View): # CORREÇÃO: Mixin de filial não funciona aqui
    def get(self, request, *args, **kwargs):
        # CORREÇÃO: Aplicando o filtro de filial manualmente.
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
    

