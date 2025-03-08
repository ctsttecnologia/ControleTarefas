from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Logradouro, Cliente, ClienteCliente
from django.contrib.auth.decorators import login_required
from .forms import ClienteForm


@login_required
def cliente(request):
    return render(request, 'cliente/cliente.html')

@login_required
def lista_clientes(request):
   return render(request, 'cliente/lista_clientes.html')


@login_required
def cadastro_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()  # Salva os dados no banco de dados
            return redirect('lista_clientes')  # Redireciona para uma página de sucesso
    else:
        form = ClienteForm()  # Cria um formulário vazio para GET requests

    return render(request, 'cliente/cadastro_cliente.html', {'form': form})

def salvar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()  # Salva os dados no banco de dados
            return redirect('lista_clientes')  # Redireciona para uma página de sucesso
    else:
        form = ClienteForm()  # Cria um formulário vazio para GET requests

    return render(request, 'cliente/cadastro_cliente.html', {'form': form}) 