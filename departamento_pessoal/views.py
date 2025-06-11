from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.template.loader import get_template
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.views.generic import DetailView

from xhtml2pdf import pisa
import csv
from .forms import AdmissaoForm, DepartamentoForm, CboForm, CargoForm, DocumentosForm, FuncionarioForm, DocumentosEditForm
from .models import Funcionarios, Admissao, Documentos, Cargos, Departamentos, Cbos



@login_required
def departamento_pessoal(request):
    """View inicial do departamento pessoal"""
    return render(request, 'departamento_pessoal/departamento_pessoal.html')

@login_required
def profile_view(request):
    """View do perfil do usuário"""
    return render(request, 'usuario/profile.html')

@login_required
def lista_funcionarios(request):
    queryset = Funcionarios.objects.select_related('admissao').all()
    matricula = request.GET.get('matricula')
    
    if matricula:
        queryset = queryset.filter(admissao__matricula__icontains=matricula)
    
    # Configura a paginação (30 itens por página)
    paginator = Paginator(queryset, 30)
    page_number = request.GET.get('page')
    
    try:
        funcionarios = paginator.page(page_number)
    except PageNotAnInteger:
        # Se o parâmetro page não for um inteiro, mostra a primeira página
        funcionarios = paginator.page(1)
    except EmptyPage:
        # Se a página estiver fora do intervalo (ex. 9999), mostra a última página
        funcionarios = paginator.page(paginator.num_pages)
    
    return render(request, 'departamento_pessoal/lista_funcionarios.html', {
        'funcionarios': funcionarios
    })

@login_required
@permission_required('departamento_pessoal.add_funcionarios', raise_exception=True)
def cadastrar_funcionario(request):
    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            funcionario = form.save()
            messages.success(request, 'Funcionário cadastrado com sucesso!')
            return redirect('departamento_pessoal:cadastrar_documentos', funcionario_pk=funcionario.pk)
    else:
        form = FuncionarioForm()
    
    return render(request, 'departamento_pessoal/cadastrar_funcionario.html', {'form': form})

@login_required
def cadastrar_documentos(request, funcionario_pk):
    funcionario = get_object_or_404(Funcionarios, pk=funcionario_pk)
    departamento = getattr(funcionario, 'departamento', None)
    admissao = getattr(funcionario, 'admissao', None)

    context = {
        'form': DocumentosForm(initial={'funcionario_id': funcionario.id}),
        'departamento': departamento,
        'funcionario': funcionario,
        'admissao': admissao
    }
    return render(request, 'departamento_pessoal/cadastrar_documentos.html', context)

    # Verifica se já existe documento para este funcionário
    try:
        documento_existente = Documentos.objects.get(funcionario=funcionario)
        return redirect('departamento_pessoal:editar_documentos', funcionario_pk=funcionario.pk)
    except Documentos.DoesNotExist:
        pass

    if request.method == 'POST':
        form = DocumentosForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.funcionario = funcionario
            
            # Configura valores padrão
            documento.sigla = 'DOC'
            documento.nome = 'Documentos Pessoais'
            
            try:
                documento.departamento = Departamentos.objects.get(nome='Departamento Pessoal')
            except Departamentos.DoesNotExist:
                documento.departamento = Departamentos.objects.create(
                    nome='Departamento Pessoal',
                    sigla='DP'
                )
            
            try:
                documento.save()
                messages.success(request, 'Documentos cadastrados com sucesso!')
                return redirect('departamento_pessoal:detalhe_funcionario', pk=funcionario.pk)
            except IntegrityError as e:
                messages.error(request, f'Erro ao salvar documentos: {str(e)}')
            except Exception as e:
                messages.error(request, f'Erro inesperado: {str(e)}')
        else:
            messages.error(request, 'Por favor, corrija os erros no formulário.')
    else:
        form = DocumentosForm()

    return render(request, 'departamento_pessoal/cadastrar_documentos.html', {
        'form': form,
        'funcionario': funcionario
    })

@login_required
def cadastrar_documentos(request, funcionario_pk):
    funcionario = get_object_or_404(Funcionarios, pk=funcionario_pk)
    
    # Verifica se já existe documento para este funcionário
    if Documentos.objects.filter(funcionario=funcionario).exists():
        return redirect('departamento_pessoal:editar_documentos', funcionario_pk=funcionario.pk)

    departamento = getattr(funcionario, 'departamento', None)
    admissao = getattr(funcionario, 'admissao', None)

    if request.method == 'POST':
        form = DocumentosForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.funcionario = funcionario
            documento.sigla = 'DOC'
            documento.nome = 'Documentos Pessoais'
            documento.tipo = 'PES'
            documento.ativo = True
            
            # Define departamento padrão se não existir
            if not departamento:
                departamento, created = Departamentos.objects.get_or_create(
                    nome='Departamento Pessoal',
                    defaults={'sigla': 'DP'}
                )
            documento.departamento = departamento

            try:
                documento.save()
                messages.success(request, 'Documentos cadastrados com sucesso!')
                return redirect('departamento_pessoal:detalhe_funcionario', pk=funcionario.pk)
            except IntegrityError as e:
                messages.error(request, f'Erro ao salvar documentos: {str(e)}')
            except Exception as e:
                messages.error(request, f'Erro inesperado: {str(e)}')
    else:
        initial_data = {
            'funcionario_id': funcionario.id,
            'departamento': departamento.id if departamento else None
        }
        form = DocumentosForm(initial=initial_data)

    context = {
        'form': form,
        'funcionario': funcionario,
        'departamento': departamento,
        'admissao': admissao,
        'titulo_pagina': 'Cadastrar Documentos Pessoais'
    }
    return render(request, 'departamento_pessoal/cadastrar_documentos.html', context)


class FuncionarioDetailView(DetailView):
    model = Funcionarios
    template_name = 'departamento_pessoal/detalhe_funcionario.html'
    context_object_name = 'funcionario'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Você pode adicionar mais contexto aqui se necessário
        return context

@login_required
def detalhe_funcionario(request, pk):
    funcionario = get_object_or_404(Funcionarios, pk=pk)
    context = {
        'funcionario': funcionario,
    }
    return render(request, 'departamento_pessoal/detalhe_funcionario.html', context)

@login_required
@permission_required('departamento_pessoal.change_funcionarios', raise_exception=True)
def editar_funcionario(request, pk):
    funcionario = get_object_or_404(Funcionarios, pk=pk)
    
    if request.method == 'POST':
        form = FuncionarioForm(request.POST, instance=funcionario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Funcionário atualizado com sucesso!')
            return redirect('departamento_pessoal:detalhe_funcionario', pk=pk)
    else:
        form = FuncionarioForm(instance=funcionario)
    
    return render(request, 'departamento_pessoal/editar_funcionario.html', {
        'form': form,
        'funcionario': funcionario
    })

# check_email_exists
@login_required
@permission_required('departamento_pessoal.change_funcionarios', raise_exception=True)
def check_email_exists(request):
    email = request.GET.get('email', '')
    try:
        exists = Funcionarios.objects.filter(email=email).exists() 
        return JsonResponse({'exists': exists})
    except ValidationError:
        return JsonResponse({'exists': False})

@login_required
@permission_required('departamento_pessoal.delete_funcionarios', raise_exception=True)
def confirmar_exclusao(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)
    if request.method == 'POST':
        funcionario.delete()
        return redirect('lista_funcionarios')
    return render(request, 'confirmar_exclusao.html', {'funcionario': funcionario})

@login_required
def buscar_funcionario_por_matricula(request):
    """View para busca AJAX de funcionário por matrícula"""
    matricula = request.GET.get('matricula')
    
    if not matricula:
        return JsonResponse({'error': 'Parâmetro matrícula é obrigatório'}, status=400)
    
    try:
        funcionario = Funcionarios.objects.get(admissao__matricula=matricula)
        data = {
            'nome': funcionario.nome,
            'cargo': funcionario.admissao.cargo.nome if hasattr(funcionario, 'admissao') else '',
            'admissao': funcionario.admissao.data_admissao.strftime('%Y-%m-%d') if hasattr(funcionario, 'admissao') else '',
        }
        return JsonResponse(data)
        
    except Funcionarios.DoesNotExist:
        return JsonResponse({'error': 'Funcionário não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

"""Cria uma nova admissão"""
class NovaAdmissaoView(PermissionRequiredMixin, CreateView):
    permission_required = 'departamento_pessoal.add_admissao'
    model = Admissao
    form_class = AdmissaoForm
    template_name = 'departamento_pessoal/nova_admissao.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['funcionario'] = self.kwargs['funcionario_pk']
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['funcionario'] = get_object_or_404(Funcionarios, pk=self.kwargs['funcionario_pk'])
        return context

    def form_valid(self, form):
        form.instance.funcionario = get_object_or_404(Funcionarios, pk=self.kwargs['funcionario_pk'])
        
        # Gera matrícula automática se não for fornecida
        if not form.cleaned_data.get('matricula'):
            ultima_matricula = Admissao.objects.order_by('-matricula').first()
            nova_matricula = int(ultima_matricula.matricula) + 1 if ultima_matricula else 1000
            form.instance.matricula = str(nova_matricula).zfill(4)
        
        response = super().form_valid(form)
        messages.success(self.request, 'Admissão cadastrada com sucesso!')
        return response

    def get_success_url(self):
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.funcionario.pk})

class DetalhesAdmissaoView(DetailView):
    model = Admissao
    template_name = 'departamento_pessoal/detalhes_admissao.html'
    context_object_name = 'admissao'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['funcionario'] = self.object.funcionario
        return context

"""Lista todas as admissões"""
class ListaAdmissoesView(PermissionRequiredMixin, ListView):
    permission_required = 'departamento_pessoal.view_admissao'
    model = Admissao
    template_name = 'departamento_pessoal/lista_admissoes.html'
    context_object_name = 'admissoes'
    queryset = Admissao.objects.select_related('funcionario', 'cargo', 'departamento')
    paginate_by = 20
    
    def form_valid(self, form):
        # Garante que o funcionário está correto
        form.instance.funcionario = get_object_or_404(Funcionarios, pk=self.kwargs['funcionario_pk'])
        
        # Processa os dias da semana
        dias_semana = form.cleaned_data.get('dias_semana', '')
        if isinstance(dias_semana, list):
            form.instance.dias_semana = ','.join(dias_semana)
        
        response = super().form_valid(form)
        messages.success(self.request, 'Admissão cadastrada com sucesso!')
        return response
    
    def get_success_url(self):
        return reverse('departamento_pessoal:detalhes_funcionario',
                     kwargs={'pk': self.object.funcionario.pk})

"""Edita uma admissão existente"""
class EditarAdmissaoView(PermissionRequiredMixin, UpdateView):
    permission_required = 'departamento_pessoal.change_admissao'
    model = Admissao
    form_class = AdmissaoForm
    template_name = 'departamento_pessoal/editar_admissao.html'
    context_object_name = 'admissao'

    def get_success_url(self):
        messages.success(self.request, 'Admissão atualizada com sucesso!')
        return reverse('departamento_pessoal:detalhes_funcionario', 
                     kwargs={'pk': self.object.funcionario.pk})

# Views para relatórios
@login_required
def exportar_funcionarios_pdf(request):
    """Gera relatório PDF de funcionários"""
    funcionarios = Funcionarios.objects.select_related('admissao', 'documentos').all()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="funcionarios.pdf"'
    
    template = get_template('departamento_pessoal/relatorios/funcionarios_pdf.html')
    html = template.render({'funcionarios': funcionarios})
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF')
    return response

@login_required
def exportar_admissoes_csv(request):
    """Gera relatório CSV de admissões"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="admissoes.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Matrícula', 'Nome', 'Cargo', 'Departamento', 
        'Data Admissão', 'Salário', 'Tipo Contrato'
    ])
    
    admissoes = Admissao.objects.select_related('funcionario', 'cargo', 'departamento')
    for adm in admissoes:
        writer.writerow([
            adm.matricula,
            adm.funcionario.nome,
            adm.cargo.nome,
            adm.departamento.nome,
            adm.data_admissao.strftime('%d/%m/%Y'),
            adm.salario,
            adm.get_tipo_contrato_display()
        ])
    
    return response

class CadastroAuxiliarView(PermissionRequiredMixin, TemplateView):
    permission_required = ['departamento_pessoal.view_departamentos', 
                         'departamento_pessoal.view_cbos',
                         'departamento_pessoal.view_cargos']
    template_name = 'departamento_pessoal/cadastro_auxiliar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departamentos'] = Departamentos.objects.all().order_by('nome')
        context['cbos'] = Cbos.objects.all().order_by('codigo')
        context['cargos'] = Cargos.objects.all().order_by('nome')
        context['departamento_form'] = DepartamentoForm()
        context['cbo_form'] = CboForm()
        context['cargo_form'] = CargoForm()
        return context

class CadastrarDepartamentoView(PermissionRequiredMixin, CreateView):
    permission_required = 'departamento_pessoal.add_departamentos'
    model = Departamentos
    form_class = DepartamentoForm
    success_url = reverse_lazy('departamento_pessoal:cadastro_auxiliar')
    
    def form_valid(self, form):
        messages.success(self.request, 'Departamento cadastrado com sucesso!')
        return super().form_valid(form)

class CadastrarCboView(PermissionRequiredMixin, CreateView):
    permission_required = 'departamento_pessoal.add_cbos'
    model = Cbos
    form_class = CboForm
    success_url = reverse_lazy('departamento_pessoal:cadastro_auxiliar')
    
    def form_valid(self, form):
        messages.success(self.request, 'CBO cadastrado com sucesso!')
        return super().form_valid(form)

class CadastrarCargoView(PermissionRequiredMixin, CreateView):
    permission_required = 'departamento_pessoal.add_cargos'
    model = Cargos
    form_class = CargoForm
    success_url = reverse_lazy('departamento_pessoal:cadastro_auxiliar')
    
    def form_valid(self, form):
        messages.success(self.request, 'Cargo cadastrado com sucesso!')
        return super().form_valid(form)

