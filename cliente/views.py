from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import ClienteForm
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from .models import Cliente
from django.views.decorators.csrf import csrf_exempt, csrf_protect, requires_csrf_token


@csrf_exempt
@csrf_protect
@requires_csrf_token
@login_required
def cliente(request):
    return render(request, 'cliente/cliente.html')

@login_required
def lista_clientes(request):
    nome = request.GET.get('nome')
    cnpj = request.GET.get('cnpj')
    razao_social = request.GET.get('razao_social')

    clientes = Cliente.objects.all()

    if nome:
        clientes = clientes.filter(nome__icontains=nome)
    if cnpj:
        clientes = clientes.filter(cnpj__icontains=cnpj)
    if razao_social:
        clientes = clientes.filter(razao_social__icontains=razao_social)

    return render(request, 'cliente/resultadopesquisa.html', {'clientes': clientes})

@login_required
def cadastro_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()  # Salva os dados no banco de dados
            return redirect('cadastro_cliente.html')  # Redireciona para uma página de sucesso
    else:
        form = ClienteForm()  # Cria um formulário vazio para GET requests

    return render(request, 'cliente/cadastro_cliente.html', {'form': form})

@login_required
def salvar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()  # Salva os dados no banco de dados
            return redirect('lista_clientes')  # Redireciona para uma página de sucesso
    else:
        form = ClienteForm()  # Cria um formulário vazio para GET requests

    return render(request, 'cliente/cadastro_cliente.html', {'form': form}) 

@login_required  # Garante que apenas usuários logados acessem o perfil
def profile_view(request):
    return render(request, 'usuario/profile.html')  # Renderiza o template do perfil


def excluir_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)  # Busca o cliente pelo ID
    if request.method == 'POST':
        cliente.delete()  # Exclui o cliente
        return redirect(reverse('lista_clientes'))  # Redireciona para a lista de clientes
    return redirect(reverse('cliente/cadastro_cliente.html'))  # Redireciona se não for POST
