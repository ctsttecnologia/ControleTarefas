from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import Logradouro
from .forms import LogradouroForm
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt, csrf_protect, requires_csrf_token


@csrf_exempt
@csrf_protect
@requires_csrf_token

@login_required
def cadastro(request):
    # Listar logradouros
    if request.method == 'POST':
        form = LogradouroForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('cadastro')  # Redireciona para a mesma página após salvar
    else:
        form = LogradouroForm()

    logradouros = Logradouro.objects.all()  # Lista todos os logradouros
    return render(request, 'cadastros/cadastro.html', {'form': form, 'logradouros': logradouros})

@login_required
def logradouro(request):
    # Cadastrar logradouros
    if request.method == 'POST':
        form = LogradouroForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('cadastro')  # Redireciona para a mesma página após salvar
    else:
        form = LogradouroForm()

    logradouros = Logradouro.objects.all()  # Lista todos os logradouros
    return render(request, 'cadastros/logradouro.html', {'form': form, 'logradouros': logradouros})


@login_required
def editar_logradouro(request, pk):
    # Editar logradouro
    logradouro = get_object_or_404(Logradouro, pk=pk)
    if request.method == 'POST':
        form = LogradouroForm(request.POST, instance=logradouro)
        if form.is_valid():
            form.save()
            return redirect('cadastro')  # Redireciona para a página de cadastro
    else:
        form = LogradouroForm(instance=logradouro)

    return render(request, 'cadastros/editar_logradouro.html', {'form': form})

@login_required
def excluir_logradouro(request, pk):
    # Excluir logradouro
    logradouro = get_object_or_404(Logradouro, pk=pk)
    if request.method == 'POST':
        logradouro.delete()
        return redirect('cadastro')  # Redireciona para a página de cadastro
    return render(request, 'cadastros/confirmar_exclusao.html', {'logradouro': logradouro})

@login_required  # Garante que apenas usuários logados acessem o perfil
def profile_view(request):
    return render(request, 'usuario/profile.html')  # Renderiza o template do perfil

