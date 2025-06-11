
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt, csrf_protect, requires_csrf_token
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator

from .models import FichaEPI
from .forms import EquipamentosSegurancaForm
from reportlab.pdfgen import canvas
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from seguranca_trabalho.models import EPIEquipamentoSeguranca


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
    # Obtenha todos os equipamentos inicialmente
    equipamentos = EPIEquipamentoSeguranca.objects.all().order_by('nome_equipamento')
    
    # Processar filtros
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Aplicar filtro de pesquisa
    if search_query:
        equipamentos = equipamentos.filter(
            Q(nome_equipamento__icontains=search_query) |
            Q(descricao__icontains=search_query) |
            Q(codigo_ca__icontains=search_query)
        )
    
    # Aplicar filtro de status
    if status_filter == 'ativo':
        equipamentos = equipamentos.filter(ativo=True)
    elif status_filter == 'inativo':
        equipamentos = equipamentos.filter(ativo=False)
    
    # Configurar paginação
    paginator = Paginator(equipamentos, 10)  # 10 itens por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'equipamentos': page_obj.object_list,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'seguranca_trabalho/listar_equipamentos.html', context)

@login_required
def verificar_codigo_ca(request):
    if request.method == 'POST':
 
        codigo = request.POST.get('codigo')
     
        return JsonResponse({'valid': True})  
    return JsonResponse({'error': 'Invalid request'}, status=400)

# Cadastrar novo equipamento
@login_required
def cadastrar_equipamento(request):
    if request.method == 'POST':
        form = EquipamentosSegurancaForm(request.POST) 
        if form.is_valid():
            form.save()
            messages.success(request, 'Item cadastrado com sucesso!')
            return redirect('seguranca_trabalho:cadastrar_equipamento')
    else:
        form = EquipamentosSegurancaForm()
    
    return render(request, 'seguranca_trabalho/cadastrar_equipamento.html', {
        'form': form,
        'titulo': 'Cadastro de Equipamento'
    })

# Editar equipamento existente
@login_required
def editar_equipamento(request, id):
    equipamento = get_object_or_404(EPIEquipamentoSeguranca, id=id)
    if request.method == 'POST':
        form = EquipamentosSegurancaForm(request.POST, instance=equipamento)
        if form.is_valid():
            # Salva o formulário mas mantém a data de validade original
            equipamento_editado = form.save(commit=False)
            equipamento_editado.data_validade = equipamento.data_validade  # Mantém o valor original
            equipamento_editado.save()
            messages.success(request, 'Equipamento atualizado com sucesso!')
            return redirect('seguranca_trabalho:listar_equipamentos')
    else:
        form = EquipamentosSegurancaForm(instance=equipamento)
    
    return render(request, 'seguranca_trabalho/editar_equipamento.html', {
        'form': form,
        'equipamento': equipamento
    })

# Excluir equipamento
@login_required
def excluir_equipamento(request, id):
    equipamento = get_object_or_404(EPIEquipamentoSeguranca, id=id)
    equipamento.delete()
    return redirect('seguranca_trabalho:listar_equipamentos')

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
    ws.append([
        "Nome do Colaborador",
        "Equipamento", 
        "Código CA", 
        "Data de Entrega", 
        "Data de Devolução", 
        "Contrato ID", 
        "Quantidade", 
        "Descrição"
    ])

    # Dados do formulário
    fichas = FichaEPI.objects.all()
    for ficha in fichas:
        ws.append([
        ficha.nome_colaborador, 
        ficha.equipamento, 
        ficha.ca_equipamento, 
        ficha.data_entrega, 
        ficha.data_devolucao, 
        ficha.contrato_id, 
        ficha.quantidade, 
        ficha.descricao
    ])

    wb.save(response)
    return respons

#exportar lista para exel
@login_required
def exportar_equipamentos_excel(request):
    equipamentos = EquipamentosSeguranca.objects.all()
    
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="equipamentos_seguranca.xlsx"'
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Equipamentos de Segurança"
    
    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="3498db", end_color="3498db", fill_type="solid")
    header_alignment = Alignment(horizontal="center")
    thin_border = Border(left=Side(style='thin'), 
                         right=Side(style='thin'), 
                         top=Side(style='thin'), 
                         bottom=Side(style='thin'))
    
    # Cabeçalhos
    columns = [
        ("Nome do Equipamento", 30),
        ("Tipo", 15),
        ("Código CA", 12),
        ("Descrição", 40),
        ("Quantidade", 12),
        ("Estoque Mínimo", 12),
        ("Data Validade", 12),
        ("Status", 10)
    ]
    
    for col_num, (column_title, column_width) in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_num, value=column_title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(col_num)].width = column_width
    
    # Dados
    for row_num, equipamento in enumerate(equipamentos, 2):
        ws.cell(row=row_num, column=1, value=equipamento.nome_equipamento).border = thin_border
        ws.cell(row=row_num, column=2, value=equipamento.get_tipo_display()).border = thin_border
        ws.cell(row=row_num, column=3, value=equipamento.codigo_ca).border = thin_border
        ws.cell(row=row_num, column=4, value=equipamento.descricao).border = thin_border
        
        qtd_cell = ws.cell(row=row_num, column=5, value=equipamento.quantidade_estoque)
        qtd_cell.border = thin_border
        if equipamento.quantidade_estoque < equipamento.estoque_minimo:
            qtd_cell.fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")
        
        ws.cell(row=row_num, column=6, value=equipamento.estoque_minimo).border = thin_border
        
        data_cell = ws.cell(row=row_num, column=7, 
                           value=equipamento.data_validade.strftime("%d/%m/%Y") if equipamento.data_validade else "-")
        data_cell.border = thin_border
        if equipamento.data_validade and equipamento.data_validade < timezone.now().date():
            data_cell.fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")
        
        status_cell = ws.cell(row=row_num, column=8, value="Ativo" if equipamento.ativo else "Inativo")
        status_cell.border = thin_border
        if equipamento.ativo:
            status_cell.fill = PatternFill(start_color="99FF99", end_color="99FF99", fill_type="solid")
        else:
            status_cell.fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")
    
    wb.save(response)
    return response

