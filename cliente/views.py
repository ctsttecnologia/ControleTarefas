
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse

from .models import Cliente
from .forms import ClienteForm
from logradouro.models import Logradouro

import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter


@login_required
def lista_clientes(request):
    clientes = Cliente.objects.select_related('logradouro').order_by('nome')
    return render(request, 'cliente/lista_clientes.html', {'clientes': clientes})


@login_required
def cadastro_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente cadastrado com sucesso!')
            return redirect('cliente:lista_clientes')
    else:
        form = ClienteForm()
    
    return render(request, 'cliente/cadastro_cliente.html', {'form': form})


@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente atualizado com sucesso!')
            return redirect('cliente:lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
    
    return render(request, 'cliente/editar_cliente.html', {
        'form': form,
        'object': cliente
    })

@login_required
def excluir_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, 'Cliente excluído com sucesso!')
        return redirect('cliente:lista_clientes')
    
    return render(request, 'cliente/confirmar_exclusao.html', {'cliente': cliente})

@login_required
def pesquisar_clientes(request):
    nome = request.GET.get('nome', '')
    cnpj = request.GET.get('cnpj', '')

    clientes = Cliente.objects.all()
    if nome:
        clientes = clientes.filter(nome__icontains=nome)
    if cnpj:
        clientes = clientes.filter(cnpj__icontains=cnpj)

    return render(request, 'cliente/lista_clientes.html', {
        'clientes': clientes,
        'pesquisa': True,
        'termo_nome': nome,
        'termo_cnpj': cnpj
    })


@login_required
def exportar_clientes_excel(request):
    clientes = Cliente.objects.select_related('logradouro').order_by('nome')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clientes"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    even_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'),
                    top=Side(style='thin'), bottom=Side(style='thin'))
    center = Alignment(horizontal='center')

    headers = [
        "ID", "Nome", "Endereço", "Número", "Complemento", "Bairro",
        "Cidade", "Estado", "CEP", "Contrato", "Razão Social", "Unidade",
        "CNPJ", "Telefone", "Data Início", "Status"
    ]

    # Cabeçalhos
    for i, header in enumerate(headers, 1):
        col_letter = get_column_letter(i)
        cell = ws[f"{col_letter}1"]
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = center
        ws.column_dimensions[col_letter].width = max(len(header) + 2, 12)

    # Linhas
    for idx, cliente in enumerate(clientes, start=2):
        logradouro = cliente.logradouro
        row_fill = even_fill if idx % 2 == 0 else PatternFill(fill_type=None)

        def safe(value, default=""):
            return value if value else default

        def format_cep(cep):
            return f"{cep[:5]}-{cep[5:]}" if cep and len(cep) == 8 else safe(cep)

        def format_cnpj(cnpj):
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}" if cnpj and len(cnpj) == 14 else safe(cnpj)

        def format_telefone(telefone):
            if telefone:
                if len(telefone) == 11:
                    return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
                elif len(telefone) == 10:
                    return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
            return safe(telefone)

        dados = [
            cliente.id,
            cliente.nome,
            safe(logradouro.endereco),
            safe(logradouro.numero),
            safe(logradouro.complemento),
            safe(logradouro.bairro),
            safe(logradouro.cidade),
            safe(logradouro.estado),
            format_cep(safe(logradouro.cep)),
            cliente.contrato,
            cliente.razao_social,
            cliente.unidade if cliente.unidade is not None else "",
            format_cnpj(cliente.cnpj),
            format_telefone(cliente.telefone),
            cliente.data_de_inicio.strftime('%d/%m/%Y') if cliente.data_de_inicio else "",
            "Ativo" if cliente.estatus else "Inativo"
        ]

        for col_num, value in enumerate(dados, 1):
            cell = ws.cell(row=idx, column=col_num, value=value)
            cell.border = border
            cell.fill = row_fill
            if col_num in [1, 10, 12, 15, 16]:
                cell.alignment = center

    ws.freeze_panes = "A2"

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': 'attachment; filename="clientes.xlsx"',
            'Cache-Control': 'no-cache',
        }
    )
    wb.save(response)
    return response



