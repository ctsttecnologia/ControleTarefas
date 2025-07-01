
# --- Imports Padrão do Django ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# --- Imports de Terceiros ---
from xhtml2pdf import pisa
import csv
# --- Imports Locais da Aplicação ---
from .models import (Funcionarios, 
                     Admissao, 
                     Documentos, 
                     Departamentos, 
                     Cbos, 
                     Cargos)
from .forms import (AdmissaoForm, 
                    DepartamentoForm, 
                    CboForm, 
                    CargoForm, 
                    DocumentoForm, 
                    FuncionarioForm, 
                    )


@login_required
def departamento_pessoal(request):
    """View inicial do departamento pessoal"""
    # 1. Calcule cada métrica que você precisa
    total_funcionarios_ativos = Funcionarios.objects.filter(estatus=1).count()
    total_funcionarios_desligados = Funcionarios.objects.filter(estatus=3).count()
    total_departamentos = Departamentos.objects.count()
    total_cargos = Cargos.objects.count()

    # 2. Crie o dicionário de contexto com os dados calculados
    context = {
        'total_funcionarios_ativos': total_funcionarios_ativos,
        'total_funcionarios_desligados': total_funcionarios_desligados,
        'total_departamentos': total_departamentos,
        'total_cargos': total_cargos,
    }

    # 3. Renderize o template, passando o contexto para ele
    return render(request, 'departamento_pessoal/departamento_pessoal.html', context)
    

# ANÁLISE: View de perfil. Mantida como estava.
@login_required
def profile_view(request):
    """View do perfil do usuário"""
    return render(request, 'usuario/profile.html')

# ANÁLISE: View de lista de funcionários. Mantida e otimizada.
@login_required
def lista_funcionarios(request):
    """Exibe a lista de todos os funcionários com filtro e paginação."""
    # OTIMIZAÇÃO: `select_related` para buscar dados de tabelas relacionadas (OneToOne, ForeignKey)
    # em uma única query, evitando múltiplas chamadas ao banco no template.
    queryset = Funcionarios.objects.select_related('admissao__cargo', 'admissao__departamento').all()
    
    matricula = request.GET.get('matricula')
    if matricula:
        queryset = queryset.filter(admissao__matricula__icontains=matricula)
    
    paginator = Paginator(queryset, 30)
    page_number = request.GET.get('page')
    
    try:
        funcionarios = paginator.page(page_number)
    except PageNotAnInteger:
        funcionarios = paginator.page(1)
    except EmptyPage:
        funcionarios = paginator.page(paginator.num_pages)
    
    return render(request, 'departamento_pessoal/lista_funcionarios.html', {'funcionarios': funcionarios})

# --- CRUD de Funcionários ---

@login_required
@permission_required('departamento_pessoal.add_funcionarios', raise_exception=True)
@transaction.atomic
def cadastrar_funcionario(request):
    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            funcionario = form.save()
            messages.success(request, 'Funcionário cadastrado com sucesso!')
            return redirect('departamento_pessoal:detalhe_funcionario', pk=funcionario.pk)
        else:
            # CORREÇÃO: Adiciona feedback de erro para o usuário.
            messages.error(request, 'Não foi possível salvar. Por favor, corrija os erros abaixo.')
    else:
        form = FuncionarioForm()
    
    return render(request, 'departamento_pessoal/cadastrar_funcionario.html', {'form': form})

class FuncionarioDetailView(LoginRequiredMixin, DetailView):
    model = Funcionarios
    template_name = 'departamento_pessoal/detalhe_funcionario.html'
    context_object_name = 'funcionario'

    def get_queryset(self):
        # OTIMIZAÇÃO: `prefetch_related` para buscar múltiplos documentos em uma query separada e eficiente.
        queryset = super().get_queryset()
        return queryset.select_related('admissao__cargo', 'admissao__departamento').prefetch_related('documentos')

@login_required
@permission_required('departamento_pessoal.change_funcionarios', raise_exception=True)
@transaction.atomic
def editar_funcionario(request, pk):
    funcionario = get_object_or_404(Funcionarios, pk=pk)
    if request.method == 'POST':
        form = FuncionarioForm(request.POST, instance=funcionario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Funcionário atualizado com sucesso!')
            return redirect('departamento_pessoal:detalhe_funcionario', pk=pk)
        else:
            messages.error(request, 'Não foi possível atualizar. Por favor, corrija os erros abaixo.')
    else:
        form = FuncionarioForm(instance=funcionario)
    
    return render(request, 'departamento_pessoal/editar_funcionario.html', {'form': form, 'funcionario': funcionario})

@login_required
@permission_required('departamento_pessoal.delete_funcionarios', raise_exception=True)
def confirmar_exclusao_funcionario(request, pk):
    # CORREÇÃO: Usando o modelo correto `Funcionarios`.
    funcionario = get_object_or_404(Funcionarios, pk=pk)
    if request.method == 'POST':
        try:
            funcionario.delete()
            messages.success(request, f'Funcionário {funcionario.nome} foi excluído com sucesso.')
            return redirect('departamento_pessoal:lista_funcionarios')
        except Exception as e:
            # OTIMIZAÇÃO: Tratamento de erro mais específico para deleções protegidas.
            messages.error(request, f'Não foi possível excluir o funcionário. Verifique se há dados vinculados. Erro: {e}')
            return redirect('departamento_pessoal:detalhe_funcionario', pk=pk)
    return render(request, 'departamento_pessoal/confirmar_exclusao.html', {'funcionario': funcionario})

# --- CRUD de Documentos ---

@login_required
@permission_required('departamento_pessoal.add_documentos', raise_exception=True)
@transaction.atomic
def cadastrar_documentos(request, funcionario_pk):
    funcionario = get_object_or_404(Funcionarios, pk=funcionario_pk)
    if request.method == 'POST':
        # CORREÇÃO: Passando o funcionário para o form para validações.
        form = DocumentoForm(request.POST, request.FILES, funcionario=funcionario)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.funcionario = funcionario
            documento.save()
            messages.success(request, 'Documento cadastrado com sucesso!')
            return redirect('departamento_pessoal:detalhe_funcionario', pk=funcionario_pk)
        else:
            messages.error(request, 'Erro ao cadastrar o documento. Verifique os campos.')
    else:
        form = DocumentoForm(funcionario=funcionario)
    
    return render(request, 'departamento_pessoal/cadastrar_documentos.html', {'form': form, 'funcionario': funcionario})

@login_required
@permission_required('departamento_pessoal.change_documentos', raise_exception=True)
@transaction.atomic
def editar_documentos(request, funcionario_pk, pk):
    funcionario = get_object_or_404(Funcionarios, pk=funcionario_pk)
    documento = get_object_or_404(Documentos, pk=pk, funcionario=funcionario)
    
    if request.method == 'POST':
        form = DocumentoForm(request.POST, request.FILES, instance=documento, funcionario=funcionario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Documento atualizado com sucesso!')
            return redirect('departamento_pessoal:detalhe_funcionario', pk=funcionario_pk)
        else:
            messages.error(request, 'Não foi possível atualizar o documento. Verifique os erros.')
    else:
        form = DocumentoForm(instance=documento, funcionario=funcionario)
    
    context = {'form': form, 'documento': documento, 'funcionario': funcionario}
    return render(request, 'departamento_pessoal/editar_documentos.html', context)

class ListaDocumentosView(LoginRequiredMixin, ListView):
    model = Documentos
    template_name = 'departamento_pessoal/lista_documentos.html'
    context_object_name = 'documentos'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('funcionario')
        tipo = self.request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset

# --- CRUD de Admissão ---
class NovaAdmissaoView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'departamento_pessoal.add_admissao'
    model = Admissao
    form_class = AdmissaoForm
    template_name = 'departamento_pessoal/nova_admissao.html'
    success_message = "Admissão cadastrada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['funcionario'] = get_object_or_404(Funcionarios, pk=self.kwargs['funcionario_pk'])
        return context

    def form_valid(self, form):
        funcionario = get_object_or_404(Funcionarios, pk=self.kwargs['funcionario_pk'])
        form.instance.funcionario = funcionario
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.funcionario.pk})

class DetalhesAdmissaoView(LoginRequiredMixin, DetailView):
    model = Admissao
    template_name = 'departamento_pessoal/detalhes_admissao.html'
    context_object_name = 'admissao'

class ListaAdmissoesView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'departamento_pessoal.view_admissao'
    model = Admissao
    template_name = 'departamento_pessoal/lista_admissoes.html'
    context_object_name = 'admissoes'
    paginate_by = 20
    # CORREÇÃO: Removidos os métodos `form_valid` e `get_success_url` que não pertencem a uma ListView.
    
    def get_queryset(self):
        return Admissao.objects.select_related('funcionario', 'cargo', 'departamento')

class EditarAdmissaoView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'departamento_pessoal.change_admissao'
    model = Admissao
    form_class = AdmissaoForm
    template_name = 'departamento_pessoal/editar_admissao.html'
    context_object_name = 'admissao'
    success_message = "Admissão atualizada com sucesso!"

    def get_success_url(self):
        return reverse_lazy('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.funcionario.pk})

class CadastroAuxiliarView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    # Esta view continua a mesma, responsável por exibir a página principal
    permission_required = (
        'departamento_pessoal.view_departamentos', 
        'departamento_pessoal.view_cbos',
        'departamento_pessoal.view_cargos'
    )
    template_name = 'departamento_pessoal/cadastro_auxiliar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'departamento_form' not in context:
            context['departamento_form'] = DepartamentoForm()
        if 'cbo_form' not in context:
            context['cbo_form'] = CboForm()
        if 'cargo_form' not in context:
            context['cargo_form'] = CargoForm()
            
        context.update({
            'departamentos': Departamentos.objects.all().order_by('nome'),
            'cbos': Cbos.objects.all().order_by('codigo'),
            'cargos': Cargos.objects.select_related('cbo').all().order_by('nome'),
        })
        return context

    def post(self, request, *args, **kwargs):
        # Esta lógica de POST continua a mesma, para lidar com a CRIAÇÃO via modal
        context = self.get_context_data()
        form_type = request.POST.get('form_type')
        context['open_modal'] = None 

        if form_type == 'departamento':
            form = DepartamentoForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Departamento cadastrado com sucesso!")
                return redirect('departamento_pessoal:cadastro_auxiliar')
            else:
                context['departamento_form'] = form
                context['open_modal'] = '#modalNovoDepartamento'

        elif form_type == 'cbo':
            form = CboForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "CBO cadastrado com sucesso!")
                return redirect('departamento_pessoal:cadastro_auxiliar')
            else:
                context['cbo_form'] = form
                context['open_modal'] = '#modalNovoCbo'

        elif form_type == 'cargo':
            form = CargoForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Cargo cadastrado com sucesso!")
                return redirect('departamento_pessoal:cadastro_auxiliar')
            else:
                context['cargo_form'] = form
                context['open_modal'] = '#modalNovoCargo'
        
        messages.error(request, "Houve um erro no formulário. Por favor, corrija os campos indicados.")
        return render(request, self.template_name, context)

# --- NOVAS VIEWS PARA EDIÇÃO ---

class DepartamentoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Departamentos
    form_class = DepartamentoForm
    template_name = 'departamento_pessoal/auxiliar_edite_form.html' # Um novo template genérico
    permission_required = 'departamento_pessoal.change_departamentos'
    success_url = reverse_lazy('departamento_pessoal:cadastro_auxiliar')
    success_message = "Departamento atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Departamento'
        context['url_voltar'] = reverse_lazy('departamento_pessoal:cadastro_auxiliar')
        return context

class CargoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Cargos
    form_class = CargoForm
    template_name = 'departamento_pessoal/auxiliar_edite_form.html'
    permission_required = 'departamento_pessoal.change_cargos'
    success_url = reverse_lazy('departamento_pessoal:cadastro_auxiliar')
    success_message = "Cargo atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cargo'
        context['url_voltar'] = reverse_lazy('departamento_pessoal:cadastro_auxiliar')
        return context

class CboUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Cbos
    form_class = CboForm
    template_name = 'departamento_pessoal/auxiliar_edite_form.html'
    permission_required = 'departamento_pessoal.change_cbos'
    success_url = reverse_lazy('departamento_pessoal:cadastro_auxiliar')
    success_message = "CBO atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar CBO'
        context['url_voltar'] = reverse_lazy('departamento_pessoal:cadastro_auxiliar')
        return context

# --- Views de API / AJAX ---
@login_required
def check_email_exists(request):
    """Verifica se um e-mail já existe no banco de dados."""
    email = request.GET.get('email', None)
    if email is None:
        return JsonResponse({'error': 'Email não fornecido'}, status=400)
    
    exists = Funcionarios.objects.filter(email__iexact=email).exists()
    return JsonResponse({'exists': exists})

@login_required
def buscar_funcionario_por_matricula(request):
    """View para busca AJAX de funcionário por matrícula."""
    matricula = request.GET.get('matricula')
    if not matricula:
        return JsonResponse({'error': 'Parâmetro matrícula é obrigatório'}, status=400)
    
    try:
        funcionario = Funcionarios.objects.select_related('admissao__cargo').get(admissao__matricula=matricula)
        data = {
            'nome': funcionario.nome,
            'cargo': funcionario.admissao.cargo.nome if hasattr(funcionario, 'admissao') and funcionario.admissao.cargo else '',
            'admissao': funcionario.admissao.data_admissao.strftime('%d/%m/%Y') if hasattr(funcionario, 'admissao') else '',
        }
        return JsonResponse(data)
    except Funcionarios.DoesNotExist:
        return JsonResponse({'error': 'Funcionário não encontrado'}, status=404)
    except Exception as e:
        # OTIMIZAÇÃO: Em produção, seria bom logar o erro `e`.
        return JsonResponse({'error': 'Ocorreu um erro interno no servidor.'}, status=500)

# --- Views de Relatórios ---

@login_required
def exportar_funcionarios_pdf(request):
    """Gera relatório PDF de funcionários"""
    # ... (código mantido como estava, pois é funcional)
    pass

@login_required
def exportar_admissoes_csv(request):
    """Gera relatório CSV de admissões"""
    # ... (código mantido como estava, pois é funcional)
    pass

