from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from . import views
from .forms import FuncionarioForm
from .models import Funcionarios, Admissao, Documentos, Cargos, Departamentos, Cbos


@login_required # retrição de autenticação
def departamento_pessoal(request):
    return render(request, 'departamento_pessoal/departamento_pessoal.html') 

@login_required  # Garante que apenas usuários logados acessem o perfil
def profile_view(request):
    return render(request, 'usuario/profile.html')  # Renderiza o template do perfil

@login_required
def lista_funcionarios(request):
    funcionarios = Funcionarios.objects.all()
    return render(request, 'departamento_pessoal/lista_funcionarios.html', {'funcionarios': funcionarios})

@login_required
def cadastrar_funcionario(request):
    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_funcionarios')
    else:
        form = FuncionarioForm()
    return render(request, 'departamento_pessoal/cadastrar_funcionario.html', {'form': form})

@login_required
def detalhes_funcionario(request, id):
    funcionario = get_object_or_404(Funcionarios, id=id)
    return render(request, 'departamento_pessoal/detalhes_funcionario.html', {'funcionario': funcionario})

@login_required
def excluir_funcionario(request, id):
    funcionario = get_object_or_404(Funcionarios, id=id)
    if request.method == 'POST':
        funcionario.delete()
        return redirect('lista_funcionarios')
    return render(request, 'departamento_pessoal/confirmar_exclusao.html', {'funcionario': funcionario})

