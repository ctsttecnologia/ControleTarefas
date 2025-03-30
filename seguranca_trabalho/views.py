from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import FichaEPI
from .forms import FichaEPIForm
from .models import EquipamentosSeguranca
from .forms import EquipamentosSegurancaForm
from .forms import PesquisarFichaForm
from django.utils import timezone

from django.http import HttpResponse
from reportlab.pdfgen import canvas
from io import BytesIO
from openpyxl import Workbook
from django.views.decorators.csrf import csrf_exempt, csrf_protect, requires_csrf_token


@csrf_exempt
@csrf_protect
@requires_csrf_token

@login_required
def seguranca_trabalho(request):
    return render(request, 'seguranca_trabalho/seguranca_trabalho.html')

@login_required
def profile_view(request):
    return render(request, 'usuario/profile.html')

@login_required
def pesquisar_ficha(request):
    fichas = FichaEPI.objects.all()  # Busca todas as fichas inicialmente
    form = PesquisarFichaForm(request.GET or None)

    if form.is_valid():
        nome_colaborador = form.cleaned_data.get('nome_colaborador')
        equipamento = form.cleaned_data.get('equipamento')
        ca_equipamento = form.cleaned_data.get('ca_equipamento')

        # Filtra as fichas com base nos critérios de pesquisa
        if nome_colaborador:
            fichas = fichas.filter(nome_colaborador__icontains=nome_colaborador)
        if equipamento:
            fichas = fichas.filter(equipamento__icontains=equipamento)
        if ca_equipamento:
            fichas = fichas.filter(ca_equipamento__icontains=ca_equipamento)

    return render(request, 'seguranca_trabalho/listar_fichas.html', {'form': form, 'fichas': fichas})

#Equipamento EPI
# Listar todos os equipamentos

@login_required
def listar_equipamentos(request):
    equipamentos = EquipamentosSeguranca.objects.all()
    return render(request, 'seguranca_trabalho/listar_equipamentos.html', {'equipamentos': equipamentos})

# Cadastrar novo equipamento
@login_required
def cadastrar_equipamento(request):
    if request.method == 'POST':
        form = EquipamentosSegurancaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_equipamentos')
    else:
        form = EquipamentosSegurancaForm()
    return render(request, 'seguranca_trabalho/cadastrar_equipamento.html', {'form': form})

# Editar equipamento existente
@login_required
def editar_equipamento(request, id):
    equipamento = get_object_or_404(EquipamentosSeguranca, id=id)
    if request.method == 'POST':
        form = EquipamentosSegurancaForm(request.POST, instance=equipamento)
        if form.is_valid():
            form.save()
            return redirect('listar_equipamentos')
    else:
        form = EquipamentosSegurancaForm(instance=equipamento)
    return render(request, 'seguranca_trabalho/editar_equipamento.html', {'form': form, 'equipamento': equipamento})

# Excluir equipamento
@login_required
def excluir_equipamento(request, id):
    equipamento = get_object_or_404(EquipamentosSeguranca, id=id)
    equipamento.delete()
    return redirect('listar_equipamentos')

# Views para impressão de ficha PDF
@login_required
def gerar_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="ficha_epi.pdf"'

    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    # Cabeçalho do PDF
    p.drawString(100, 800, "Ficha de EPI")

    # Dados do formulário
    fichas = FichaEPI.objects.all()
    y = 780
    for ficha in fichas:
        p.drawString(100, y, f"Nome do Colaborador: {ficha.nome_colaborador}")
        p.drawString(100, y - 20, f"Equipamento: {ficha.equipamento}")
        p.drawString(100, y - 40, f"Código CA: {ficha.ca_equipamento}")
        p.drawString(100, y - 60, f"Data de Entrega: {ficha.data_entrega}")
        p.drawString(100, y - 80, f"Data de Devolução: {ficha.data_devolucao}")
        p.drawString(100, y - 100, f"Contrato ID: {ficha.contrato_id}")
        p.drawString(100, y - 120, f"Quantidade: {ficha.quantidade}")
        p.drawString(100, y - 140, f"Descrição: {ficha.descricao}")
        y -= 180  # Espaçamento entre registros

    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response


# Views para impressão de ficha Execl
@login_required
def gerar_excel(request):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="ficha_epi.xlsx"'

    wb = Workbook()
    ws = wb.active
    ws.title = "Ficha EPI"

    # Cabeçalho do Excel
    ws.append(["Nome do Colaborador", "Equipamento", "Código CA", "Data de Entrega", "Data de Devolução", "Contrato ID", "Quantidade", "Descrição"])

    # Dados do formulário
    fichas = FichaEPI.objects.all()
    for ficha in fichas:
        ws.append([ficha.nome_colaborador, ficha.equipamento, ficha.ca_equipamento, ficha.data_entrega, ficha.data_devolucao, ficha.contrato_id, ficha.quantidade, ficha.descricao])

    wb.save(response)
    return response
