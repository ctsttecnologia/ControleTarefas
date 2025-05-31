from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.template.loader import get_template
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ValidationError

from xhtml2pdf import pisa
import csv
from .forms import AdmissaoForm, FuncionarioForm, DocumentosForm
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
    """Lista todos os funcionários com paginação"""
    # Obtém todos os funcionários do banco de dados
    queryset = Funcionarios.objects.select_related('admissao', 'documentos').all()
    
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
            # Salva o funcionário sem documentos (null=True no modelo)
            funcionario = form.save(commit=False)
            funcionario.save()
            
            # Redireciona para cadastro de documentos
            return redirect('departamento_pessoal:cadastrar_documentos', funcionario_id=funcionario.id)
    else:
        form = FuncionarioForm()
    
    return render(request, 'departamento_pessoal/cadastrar_funcionario.html', {
        'form': form,
        'success': False
    })

@login_required
@permission_required('departamento_pessoal.add_documentos', raise_exception=True)
def cadastrar_documentos(request, funcionario_id):
    funcionario = get_object_or_404(Funcionarios, pk=funcionario_id)
    
    if request.method == 'POST':
        form = DocumentosForm(request.POST, request.FILES)
        if form.is_valid():
            # Cria e associa os documentos ao funcionário
            documentos = form.save()
            funcionario.documentos = documentos
            funcionario.save()
            
            messages.success(request, 'Documentos cadastrados com sucesso!')
            return redirect('departamento_pessoal:detalhes_funcionario', pk=funcionario.id)
    else:
        form = DocumentosForm()
    
    return render(request, 'departamento_pessoal/cadastrar_documentos.html', {
        'form': form,
        'funcionario': funcionario
    })

@login_required
def detalhes_funcionario(request, pk):
    """Exibe detalhes de um funcionário"""
    funcionario = get_object_or_404(
        Funcionarios.objects.select_related('admissao', 'documentos'), 
        pk=pk
    )
    return render(request, 'departamento_pessoal/detalhes_funcionario.html', {
        'funcionario': funcionario,
        'admissao': getattr(funcionario, 'admissao', None),
        'documentos': getattr(funcionario, 'documentos', None)
    })

@login_required
@permission_required('departamento_pessoal.change_funcionarios', raise_exception=True)
def editar_funcionario(request, pk):
    funcionario = get_object_or_404(Funcionarios, pk=pk)
    
    if request.method == 'POST':
        form = FuncionarioForm(request.POST, instance=funcionario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Funcionário atualizado com sucesso!')
            return redirect('departamento_pessoal:detalhes_funcionario', pk=pk)
    else:
        form = FuncionarioForm(instance=funcionario)
    
    return render(request, 'departamento_pessoal/editar_funcionario.html', {
        'form': form,
        'funcionario': funcionario
    })

@login_required
@permission_required('departamento_pessoal.change_funcionarios', raise_exception=True)
def check_email_exists(request):
    email = request.GET.get('email', '')
    try:
        exists = Funcionario.objects.filter(email=email).exists()
        return JsonResponse({'exists': exists})
    except ValidationError:
        return JsonResponse({'exists': False})

@login_required
@permission_required('departamento_pessoal.delete_funcionarios', raise_exception=True)
def excluir_funcionario(request, pk):
    """Exclui um funcionário"""
    funcionario = get_object_or_404(Funcionarios, pk=pk)
    
    if request.method == 'POST':
        funcionario.delete()
        messages.success(request, 'Funcionário excluído com sucesso!')
        return redirect('departamento_pessoal:lista_funcionarios')
    
    return render(request, 'departamento_pessoal/confirmar_exclusao.html', {
        'funcionario': funcionario
    })

"""Lista todas as admissões"""
class ListaAdmissoesView(ListView):
    permission_required = 'departamento_pessoal.add_admissao'
    model = Admissao
    template_name = 'departamento_pessoal/lista_admissao.html'
    context_object_name = 'admissoes'
    queryset = Admissao.objects.select_related('funcionario', 'cargo', 'departamento')

"""Cria uma nova admissão"""
class NovaAdmissaoView(PermissionRequiredMixin, CreateView):
    
    model = Admissao
    form_class = AdmissaoForm
    template_name = 'departamento_pessoal/edita_admissao.html'
    """Preenche dados iniciais com base no funcionário"""
    def get_initial(self):

        initial = super().get_initial()
        funcionario_pk = self.kwargs.get('funcionario_pk')
        if funcionario_pk:
            funcionario = get_object_or_404(Funcionarios, pk=funcionario_pk)
            initial['funcionario'] = funcionario
        return initial
    
    def get_success_url(self):
        messages.success(self.request, 'Admissão cadastrada com sucesso!')
        return reverse('departamento_pessoal:detalhes_funcionario', 
                      kwargs={'pk': self.object.funcionario.pk})

"""Edita uma admissão existente"""
class EditarAdmissaoView(UpdateView):
    
    permission_required = 'departamento_pessoal.change_admissao'
    model = Admissao
    form_class = AdmissaoForm
    template_name = 'departamento_pessoal/edita_admissao.html'
    
    def get_success_url(self):
        messages.success(self.request, 'Admissão atualizada com sucesso!')
        return reverse('departamento_pessoal:detalhes_funcionario', 
                      kwargs={'pk': self.object.funcionario.pk})

"""Visualização detalhada de um funcionário (versão baseada em classe)"""
class FuncionarioDetailView(DetailView):
    
    model = Funcionarios
    template_name = 'departamento_pessoal/detalhes_funcionario.html'
    context_object_name = 'funcionario'
    
    def get_queryset(self):
        return Funcionarios.objects.select_related('admissao', 'documentos')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = datetime.now()
        return context

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



