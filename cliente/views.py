from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponse 

from django.views.decorators.csrf import csrf_exempt, csrf_protect, requires_csrf_token

from .models import Cliente
from .forms import ClienteForm

from logradouro.models import Logradouro

import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter




@login_required
def lista_clientes(request):
    clientes = Cliente.objects.all().order_by('nome')
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
    
    return render(request, 'cliente/cadastro_cliente.html', {
        'form': form,
        'enderecos': Logradouro.objects.all()
    })

@login_required
def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente atualizado com sucesso!')
            return redirect('cliente:lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
    
    return render(request, 'cliente/cadastro_cliente.html', {
        'form': form,
        'enderecos': Logradouro.objects.all(),
        'edicao': True
    })

@login_required
def excluir_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, 'Cliente excluído com sucesso!')
    return redirect('cliente:lista_clientes')

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
    # Obtém todos os clientes ordenados por nome
    clientes = Cliente.objects.all().order_by('nome').select_related('logradouro')
    
    # Cria um novo workbook do Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clientes"
    
    # Define estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    even_row_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    odd_row_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    border = Border(left=Side(style='thin'), 
                   right=Side(style='thin'), 
                   top=Side(style='thin'), 
                   bottom=Side(style='thin'))
    center_aligned = Alignment(horizontal='center')
    
    # Cabeçalhos
    headers = [
        "ID", "Nome", "Endereço", "Número", "Complemento", "Bairro", 
        "Cidade", "Estado", "CEP", "Contrato", "Razão Social", "Unidade", 
        "CNPJ", "Telefone", "Data Início", "Status"
    ]
    
    # Adiciona cabeçalhos
    for col_num, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_num)
        cell = ws[f"{col_letter}1"]
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = center_aligned
        
        # Ajusta largura da coluna
        ws.column_dimensions[col_letter].width = max(len(header) + 2, 12)
    
    # Adiciona dados
    for row_num, cliente in enumerate(clientes, 2):
        # Alterna cores das linhas
        row_fill = even_row_fill if row_num % 2 == 0 else odd_row_fill
        
        # Obtém o logradouro ou None se não existir
        logradouro = cliente.logradouro
        
        # Formata CNPJ
        cnpj = cliente.cnpj
        cnpj_formatado = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}" if cnpj and len(cnpj) == 14 else cnpj
        
        # Formata telefone
        telefone = cliente.telefone
        telefone_formatado = ""
        if telefone:
            if len(telefone) == 11:
                telefone_formatado = f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
            elif len(telefone) == 10:
                telefone_formatado = f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
        
        # Formata CEP (usando atributo diretamente em vez de método)
        cep_formatado = ""
        if logradouro and logradouro.cep:
            cep = logradouro.cep
            if len(cep) == 8:
                cep_formatado = f"{cep[:5]}-{cep[5:]}"
            else:
                cep_formatado = cep
        
        # Dados da linha
        data = [
            cliente.id,
            cliente.nome,
            logradouro.endereco if logradouro else "",
            logradouro.numero if logradouro else "",
            logradouro.complemento if logradouro else "",
            logradouro.bairro if logradouro else "",
            logradouro.cidade if logradouro else "",
            logradouro.estado if logradouro else "",
            cep_formatado,  # Corrigido aqui - usando a variável já formatada
            cliente.contrato,
            cliente.razao_social,
            cliente.unidade if cliente.unidade else "",
            cnpj_formatado,
            telefone_formatado,
            cliente.data_de_inicio.strftime('%d/%m/%Y') if cliente.data_de_inicio else "",
            "Ativo" if cliente.estatus else "Inativo"
        ]
        
        # Adiciona dados na planilha
        for col_num, value in enumerate(data, 1):
            col_letter = get_column_letter(col_num)
            cell = ws[f"{col_letter}{row_num}"]
            cell.value = value
            cell.border = border
            cell.fill = row_fill
            
            # Centraliza algumas colunas
            if col_num in [1, 10, 12, 15, 16]:
                cell.alignment = center_aligned
    
    # Congela a primeira linha
    ws.freeze_panes = "A2"
    
    # Configura a resposta HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': 'attachment; filename="clientes.xlsx"',
            'Cache-Control': 'no-cache',
        },
    )
    
    # Salva o workbook na resposta
    wb.save(response)
    
    return response