from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Logradouro, Cliente, ClienteCliente
from django.contrib.auth.decorators import login_required

@login_required
def cliente(request):
    return render(request, 'cliente/cliente.html')

@login_required
def lista_clientes(request):
   return render(request, 'cliente/lista_clientes.html')

@login_required
def cadastro_cliente(request):
    logradouros = Logradouro.objects.all()
    return render(request, 'cliente/cadastro_cliente.html', {'logradouros': logradouros})

@login_required
def salvar_cliente(request):
    if request.method == 'POST':
        logradouro_id = request.POST.get('logradouro')
        contrato = request.POST.get('contrato')
        razao_social = request.POST.get('razao_social')
        unidade = request.POST.get('unidade')
        cnpj = request.POST.get('cnpj')
        telefone = request.POST.get('telefone')
        data_de_inicio = request.POST.get('data_de_inicio')
        estatus = request.POST.get('estatus')
        nome_cliente = request.POST.get('nome_cliente')

        if not all([logradouro_id, contrato, razao_social, cnpj, nome_cliente]):
            return HttpResponse("Preencha todos os campos obrigatórios.", status=400)

        cliente = Cliente(
            logradouro_id=logradouro_id,
            contrato=contrato,
            razao_social=razao_social,
            unidade=unidade,
            cnpj=cnpj,
            telefone=telefone,
            data_de_inicio=data_de_inicio,
            estatus=estatus
        )
        cliente.save()

        cliente_cliente = ClienteCliente(
            cliente=cliente,
            nome=nome_cliente
        )
        cliente_cliente.save()

        return redirect('lista_clientes')