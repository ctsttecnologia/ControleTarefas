from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Tarefas
from .forms import TarefaForm  # Criaremos o formulário depois




@login_required # retrição de autenticação
def tarefas(request):
    tarefas = Tarefas.objects.all().order_by('-data_criacao')
    return render(request, 'tarefas.html', {'tarefas': tarefas})

@login_required # retrição de autenticação
def tarefas(request):
    return render(request, 'tarefas/tarefas.html')


@login_required  # Garante que apenas usuários logados acessem o perfil
def profile_view(request):
    return render(request, 'usuario/profile.html')  # Renderiza o template do perfil


@login_required  # Garante que apenas usuários logados acessem o perfil
def criar_tarefa(request):
    if request.method == 'POST':
        form = TarefaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('consultar_tarefa')
    else:
        form = TarefaForm()
    return render(request, 'criar_tarefa.html', {'form': form})

    

@login_required  # Garante que apenas usuários logados acessem o perfil
def editar_tarefa(request, id):
    tarefas = get_object_or_404(Tarefas, id=id)
    if request.method == 'POST':
        form = TarefaForm(request.POST, instance=tarefas)
        if form.is_valid():
            form.save()
            return redirect('consultar_tarefa')
    else:
        form = TarefaForm(instance=tarefas)
    return render(request, 'editar_tarefa.html', {'form': form})

@login_required  # Garante que apenas usuários logados acessem o perfil
def excluir_tarefa(request, id):
    tarefa = get_object_or_404(Tarefa, id=id)
    if request.method == 'POST':
        tarefa.delete()
        return redirect('consultar_tarefa')
    return render(request, 'confirmar_exclusao.html', {'tarefa': tarefas})