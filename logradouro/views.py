from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
import openpyxl
from openpyxl.styles import Font

from .models import Logradouro
from .forms import LogradouroForm
from .constants import ESTADOS_BRASIL

@login_required
def listar_logradouros(request):
    logradouros = Logradouro.objects.all()
    return render(request, 'logradouro/cadastro.html', {
        'logradouros': logradouros,
        'total_logradouros': logradouros.count()
    })

@login_required
def cadastrar_logradouro(request):
    if request.method == 'POST':
        form = LogradouroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Endereço cadastrado com sucesso!'))
            return redirect('logradouro:listar')
        else:
            messages.error(request, _('Por favor, corrija os erros abaixo.'))
    else:
        form = LogradouroForm()
    
    return render(request, 'logradouro/cadastro.html', {
        'form': form,
        'ESTADOS_BRASIL': ESTADOS_BRASIL
    })

@login_required
def editar_logradouro(request, pk):
    logradouro = get_object_or_404(Logradouro, pk=pk)
    if request.method == 'POST':
        form = LogradouroForm(request.POST, instance=logradouro)
        if form.is_valid():
            form.save()
            messages.success(request, _('Endereço atualizado com sucesso!'))
            return redirect('logradouro:listar')
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
        return redirect('logradouro:listar')
    
    return render(request, 'logradouro/confirmar_exclusao.html', {
        'logradouro': logradouro
    })

@login_required
def exportar_excel(request):
    logradouros = Logradouro.objects.all()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Logradouros"
    
    headers = [
        "Endereço", "Número", "CEP", "Complemento", 
        "Bairro", "Cidade", "Estado", "País",
        "Ponto Referência", "Latitude", "Longitude",
        "Data Cadastro", "Data Atualização"
    ]
    
    for col_num, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_num)
        ws[f"{col_letter}1"] = header
        ws[f"{col_letter}1"].font = Font(bold=True)
    
    for row_num, logradouro in enumerate(logradouros, 2):
        ws[f"A{row_num}"] = logradouro.endereco
        ws[f"B{row_num}"] = logradouro.numero
        ws[f"C{row_num}"] = logradouro.cep_formatado
        ws[f"D{row_num}"] = logradouro.complemento or ""
        ws[f"E{row_num}"] = logradouro.bairro
        ws[f"F{row_num}"] = logradouro.cidade
        ws[f"G{row_num}"] = logradouro.get_estado_display()
        ws[f"H{row_num}"] = logradouro.pais
        ws[f"I{row_num}"] = logradouro.ponto_referencia or ""
        ws[f"J{row_num}"] = float(logradouro.latitude) if logradouro.latitude else ""
        ws[f"K{row_num}"] = float(logradouro.longitude) if logradouro.longitude else ""
        ws[f"L{row_num}"] = logradouro.data_cadastro.strftime('%d/%m/%Y %H:%M')
        ws[f"M{row_num}"] = logradouro.data_atualizacao.strftime('%d/%m/%Y %H:%M')
    
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=logradouros.xlsx'
    wb.save(response)
    
    return response
