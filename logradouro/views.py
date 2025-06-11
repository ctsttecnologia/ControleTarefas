from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from .models import Logradouro
from .forms import LogradouroForm
from .constant import ESTADOS_BRASIL


@login_required
def cadastrar_logradouro(request):
    if request.method == 'POST':
        form = LogradouroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Endereço cadastrado com sucesso!'))
            return redirect('logradouro:listar_logradouros')
        else:
            messages.error(request, _('Por favor, corrija os erros abaixo.'))
    else:
        form = LogradouroForm()
    
    return render(request, 'logradouro/cadastrar_logradouro.html', {
        'form': form,
        'ESTADOS_BRASIL': ESTADOS_BRASIL
    })

@login_required
def listar_logradouros(request):
    logradouros = Logradouro.objects.all()
    return render(request, 'logradouro/listar_logradouros.html', {
        'logradouros': logradouros,
        'total_logradouros': logradouros.count()
    })

@login_required
def editar_logradouro(request, pk):
    logradouro = get_object_or_404(Logradouro, pk=pk)
    if request.method == 'POST':
        form = LogradouroForm(request.POST, instance=logradouro)
        if form.is_valid():
            form.save()
            messages.success(request, _('Endereço atualizado com sucesso!'))
            return redirect('logradouro:listar_logradouros')
    else:
        form = LogradouroForm(instance=logradouro)
    
    return render(request, 'logradouro/editar_logradouro.html', {
        'form': form,
        'logradouro': logradouro
    })

@login_required
def excluir_logradouro(request, pk):
    logradouro = get_object_or_404(Logradouro, pk=pk)
    if request.method == 'POST':
        logradouro.delete()
        messages.success(request, _('Endereço excluído com sucesso!'))
        return redirect('logradouro:listar_logradouros')
    
    return render(request, 'logradouro/excluir_logradouro.html', {
        'logradouro': logradouro
    })

import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def exportar_excel(request):
    # Obtém todos os logradouros ordenados por endereço
    logradouros = Logradouro.objects.all().order_by('endereco')
    
    # Cria um novo workbook do Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Logradouros"
    
    # Define estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    even_row_fill = PatternFill(start_color="E6E6E6", end_color="E6E6E6", fill_type="solid")
    odd_row_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    center_aligned = Alignment(horizontal='center')
    right_aligned = Alignment(horizontal='right')
    
    # Cabeçalhos das colunas
    headers = [
        "Endereço", "Número", "CEP", "Complemento", 
        "Bairro", "Cidade", "Estado", "País",
        "Ponto Referência", "Latitude", "Longitude",
        "Data Cadastro", "Data Atualização"
    ]
    
    # Adiciona cabeçalhos formatados
    for col_num, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_num)
        cell = ws[f"{col_letter}1"]
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_aligned
        
        # Define largura inicial das colunas
        if col_letter in ['A', 'D', 'E', 'F', 'I']:
            ws.column_dimensions[col_letter].width = 25
        elif col_letter in ['C', 'G', 'H']:
            ws.column_dimensions[col_letter].width = 15
        else:
            ws.column_dimensions[col_letter].width = 12
    
    # Adiciona dados com formatação
    for row_num, logradouro in enumerate(logradouros, 2):
        # Alterna cores das linhas
        row_fill = even_row_fill if row_num % 2 == 0 else odd_row_fill
        
        # Formata CEP
        cep = str(logradouro.cep) if logradouro.cep else ""
        cep_formatado = f"{cep[:5]}-{cep[5:]}" if len(cep) == 8 else cep
        
        # Formata estado (para campos choice)
        estado = getattr(logradouro, 'get_estado_display', lambda: logradouro.estado)()
        
        # Prepara os dados da linha
        row_data = [
            logradouro.endereco or "",
            logradouro.numero or "",
            cep_formatado,
            logradouro.complemento or "",
            logradouro.bairro or "",
            logradouro.cidade or "",
            estado or "",
            logradouro.pais or "",
            logradouro.ponto_referencia or "",
            float(logradouro.latitude) if logradouro.latitude is not None else "",
            float(logradouro.longitude) if logradouro.longitude is not None else "",
            logradouro.data_cadastro.strftime('%d/%m/%Y %H:%M') if logradouro.data_cadastro else "",
            logradouro.data_atualizacao.strftime('%d/%m/%Y %H:%M') if logradouro.data_atualizacao else ""
        ]
        
        # Adiciona os dados na planilha
        for col_num, value in enumerate(row_data, 1):
            col_letter = get_column_letter(col_num)
            cell = ws[f"{col_letter}{row_num}"]
            cell.value = value
            cell.border = thin_border
            cell.fill = row_fill
            
            # Formatação especial para colunas numéricas e datas
            if col_letter in ['J', 'K']:  # Latitude e Longitude
                cell.number_format = '0.000000'
                cell.alignment = right_aligned
            elif col_letter in ['L', 'M']:  # Datas
                cell.alignment = center_aligned
    
    # Ajusta automaticamente a largura das colunas
    for column in ws.columns:
        column_letter = get_column_letter(column[0].column)
        if column_letter not in ['J', 'K']:  # Ignora coordenadas
            max_length = max(
                (len(str(cell.value)) for cell in column if cell.value is not None
            ))
            ws.column_dimensions[column_letter].width = min(max_length + 2, 50)
    
    # Congela a linha de cabeçalho e adiciona filtros
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    
    # Configura a resposta HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': 'attachment; filename="logradouros.xlsx"',
            'Cache-Control': 'no-cache'
        }
    )
    
    wb.save(response)
    return response