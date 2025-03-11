from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import Estados, Logradouro
from .forms import Estado, Logradouro

@login_required
def cadastro(request):
    return render(request, 'cadastros/cadastro.html')


# Views para Estados
def lista_estados(request):
    estados = Estados.objects.all()
    return render(request, 'cadastros/lista_estados.html', {'estados': estados})

def novo_estado(request):
    if request.method == "POST":
        form = Estado(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_estados')
    else:
        form = Estado()
    return render(request, 'cadastros/editar_estado.html', {'form': form})

def editar_estado(request, pk):
    estado = get_object_or_404(Estados, pk=pk)
    if request.method == "POST":
        form = Estado(request.POST, instance=estado)
        if form.is_valid():
            form.save()
            return redirect('lista_estados')
    else:
        form = Estado(instance=estado)
    return render(request, 'cadastros/editar_estado.html', {'form': form})

def deletar_estado(request, pk):
    estado = get_object_or_404(Estados, pk=pk)
    estado.delete()
    return redirect('lista_estados')

# Views para Logradouro
def lista_logradouros(request):
    logradouros = Logradouro.objects.all()
    return render(request, 'cadastros/lista_logradouros.html', {'logradouros': logradouros})

def novo_logradouro(request):
    if request.method == "POST":
        form = Logradouro(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_logradouros')
    else:
        form = Logradouro()
    return render(request, 'cadastros/editar_logradouro.html', {'form': form})

def editar_logradouro(request, pk):
    logradouro = get_object_or_404(Logradouro, pk=pk)
    if request.method == "POST":
        form = Logradouro(request.POST, instance=logradouro)
        if form.is_valid():
            form.save()
            return redirect('lista_logradouros')
    else:
        form = Logradouro(instance=logradouro)
    return render(request, 'cadastros/editar_logradouro.html', {'form': form})

def deletar_logradouro(request, pk):
    logradouro = get_object_or_404(Logradouro, pk=pk)
    logradouro.delete()
    return redirect('lista_logradouros')

@login_required  # Garante que apenas usuários logados acessem o perfil
def profile_view(request):
    return render(request, 'usuario/profile.html')  # Renderiza o template do perfil