# automovel/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import IntegrityError
from django.utils import timezone 
from django.db.models import Count, Q, Sum, Case, When, Value
from django.http import HttpResponse, JsonResponse, HttpResponseServerError
from django.db.models.functions import ExtractMonth
from django.template.loader import get_template
from django.conf import settings

from xhtml2pdf import pisa 
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
import openpyxl
import logging
import os
import io
from io import BytesIO
import json

from .relatorios import gerar_relatorio_pdf, gerar_relatorio_excel
from datetime import datetime, date
from .forms import CarroForm, AgendamentoForm
from .models import Carro, Agendamento
from .forms import ChecklistCarroForm
from .models import ChecklistCarro



@login_required
def lista_carros(request):
    carros = Carro.objects.all().order_by('marca', 'modelo')
    return render(request, 'automovel/lista_carros.html', {'carros': carros})

@login_required
@permission_required('automovel.add_carro', raise_exception=True)
def adicionar_carro(request):
    if request.method == 'POST':
        form = CarroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Carro adicionado com sucesso!')
            return redirect('automovel:lista_carros')
    else:
        form = CarroForm()
    
    return render(request, 'automovel/carro_form.html', {'form': form})

@login_required
@permission_required('automovel.change_carro', raise_exception=True)
def editar_carro(request, pk):
    carro = get_object_or_404(Carro, pk=pk)
    if request.method == 'POST':
        form = CarroForm(request.POST, instance=carro)
        if form.is_valid():
            form.save()
            messages.success(request, 'Carro atualizado com sucesso!')
            return redirect('automovel:lista_carros')
    else:
        form = CarroForm(instance=carro)
    
    return render(request, 'automovel/carro_form.html', {'form': form})

@login_required
@permission_required('automovel.delete_carro', raise_exception=True)
def excluir_carro(request, pk):
    carro = get_object_or_404(Carro, pk=pk)
    if request.method == 'POST':
        carro.delete()
        messages.success(request, 'Carro excluído com sucesso!')
        return redirect('automovel:lista_carros')
    
    return render(request, 'automovel/confirmar_exclusao.html', {'obj': carro})

@login_required
def lista_agendamentos(request):
    agendamentos = Agendamento.objects.select_related('carro').order_by('-data_hora_agenda')
    return render(request, 'automovel/lista_agendamentos.html', {'agendamentos': agendamentos})

@login_required
def adicionar_agendamento(request):
    if request.method == 'POST':
        form = AgendamentoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                agendamento = form.save(commit=False)
                if not agendamento.responsavel:
                    agendamento.responsavel = request.user.get_full_name() or request.user.username
                
                # Processamento seguro dos campos booleanos
                agendamento.abastecimento = 'abastecimento' in request.POST
                agendamento.pedagio = 'pedagio' in request.POST
                agendamento.cancelar_agenda = 'cancelar_agenda' in request.POST
                
                agendamento.save()
                messages.success(request, 'Agendamento criado com sucesso!')
                return redirect('automovel:lista_agendamentos')
            
            except IntegrityError as e:
                messages.error(request, 'Erro de integridade ao salvar o agendamento. Verifique os dados.')
                # Log do erro para debug (opcional)
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"IntegrityError ao criar agendamento: {str(e)}")
                
                return render(request, 'automovel/agendamento_form.html', {'form': form})
    else:
        form = AgendamentoForm(initial={
            'status': 'agendado',
            'responsavel': request.user.get_full_name() or request.user.username
        })
    
    return render(request, 'automovel/agendamento_form.html', {'form': form})

@login_required
def clean(self):
    cleaned_data = super().clean()
    # Conversão explícita para boolean
    cleaned_data['abastecimento'] = bool(cleaned_data.get('abastecimento'))
    return cleaned_data

@login_required
def editar_agendamento(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    if request.method == 'POST':
        form = AgendamentoForm(request.POST, request.FILES, instance=agendamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Agendamento atualizado com sucesso!')
            return redirect('automovel:lista_agendamentos')
    else:
        form = AgendamentoForm(instance=agendamento)
    
    return render(request, 'automovel/agendamento_form.html', {'form': form})

@login_required
def excluir_agendamento(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    if request.method == 'POST':
        agendamento.delete()
        messages.success(request, 'Agendamento excluído com sucesso!')
        return redirect('automovel:lista_agendamentos')
    
    return render(request, 'automovel/confirmar_exclusao.html', {'obj': agendamento})

@login_required
def assinar_agendamento(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    if request.method == 'POST':
        assinatura = request.POST.get('assinatura')
        if assinatura:
            agendamento.assinatura = assinatura
            agendamento.save()
            messages.success(request, 'Assinatura registrada com sucesso!')
            return redirect('automovel:lista_agendamentos')
    
    return render(request, 'automovel/assinar_agendamento.html', {'agendamento': agendamento})

@login_required
def agendamento_fotos(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    return render(request, 'automovel/agendamento_fotos.html', {'agendamento': agendamento})

#RELATÓRIO
@login_required
def relatorios(request):
    return render(request, 'automovel/relatorios.html')

@login_required
def exportar_pdf(request, relatorio_tipo):
    try:
        # 1. Pré-processamento dos dados
        if relatorio_tipo == 'carros':
            dados = Carro.objects.all().order_by('modelo')
            titulo = "Relatório de Veículos"
            colunas = ["ID", "Modelo", "Marca", "Placa", "Ano", "Cor", "Status"]
            
            objetos = []
            for item in dados:
                objetos.append({
                    'id': item.id,
                    'modelo': item.modelo,
                    'marca': item.marca,
                    'placa': item.placa,
                    'ano': item.ano,
                    'cor': item.get_cor_display() if hasattr(item, 'get_cor_display') else item.cor,
                    'status': item.get_status_display() if hasattr(item, 'get_status_display') else item.status
                })
                
        elif relatorio_tipo == 'agendamentos':
            dados = Agendamento.objects.select_related('carro').all().order_by('-data_hora_agenda')
            titulo = "Relatório de Agendamentos"
            colunas = ["ID", "Veículo", "Data", "Serviço", "Responsável", "Status"]
            
            objetos = []
            for item in dados:
                objetos.append({
                    'id': item.id,
                    'carro': f"{item.carro.marca} {item.carro.modelo}" if item.carro else "N/A",
                    'data': item.data_hora_agenda.strftime('%d/%m/%Y %H:%M') if item.data_hora_agenda else "N/A",
                    'servico': item.descricao[:50] + '...' if item.descricao and len(item.descricao) > 50 else (item.descricao if item.descricao else "N/A"),
                    'responsavel': item.responsavel if item.responsavel else "N/A",
                    'status': item.get_status_display() if hasattr(item, 'get_status_display') else (item.status if item.status else "N/A")
                })
        else:
            return HttpResponse("Tipo de relatório inválido", status=400)

        # 2. Preparação do contexto
        context = {
            'objetos': objetos,
            'titulo': titulo,
            'colunas': colunas,
            'data_emissao': timezone.now().strftime("%d/%m/%Y %H:%M"),
            'relatorio_tipo': relatorio_tipo
        }

        # 3. Renderização segura do template
        template = get_template('automovel/base_relatorio.html')
        html = template.render(context)
        
        # 4. Geração do PDF com tratamento de erro
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="relatorio_{relatorio_tipo}.pdf"'
        
        pdf_status = pisa.CreatePDF(
            BytesIO(html.encode('UTF-8')),
            dest=response,
            encoding='UTF-8'
        )
        
        if pdf_status.err:
            return HttpResponse(f"Erro na geração do PDF: {pdf_status.err}", status=500)
            
        return response

    except Exception as e:
        error_msg = f"Erro ao gerar relatório: {str(e)}"
        print(error_msg)  # Log no console
        return HttpResponse(error_msg, status=500)

@login_required
def exportar_excel(request, relatorio_tipo):
    # Obtenha os dados conforme o tipo de relatório
    if relatorio_tipo == 'carros':
        objetos = Carro.objects.all().order_by('modelo')
        titulo = "Relatório de Veículos"
        colunas = ["ID", "Modelo", "Marca", "Placa", "Ano", "Cor", "Status"]
    
    elif relatorio_tipo == 'agendamentos':
        objetos = Agendamento.objects.select_related('carro').all().order_by('-data_hora_agenda')
        titulo = "Relatório de Agendamentos"
        colunas = ["ID", "Veículo", "Data", "Serviço", "Responsável", "Status"]
    
    else:
        return HttpResponse("Tipo de relatório inválido", status=400)

    # Cria um novo workbook do Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = titulo[:31]  # Limita a 31 caracteres

    # Define estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    even_row_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    odd_row_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                   top=Side(style='thin'), bottom=Side(style='thin'))
    center_aligned = Alignment(horizontal='center')
    
    # Adiciona cabeçalhos
    for col_num, header in enumerate(colunas, 1):
        col_letter = get_column_letter(col_num)
        cell = ws[f"{col_letter}1"]
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = center_aligned
        ws.column_dimensions[col_letter].width = len(header) + 5

    # Adiciona dados
    for row_num, obj in enumerate(objetos, 2):
        row_fill = even_row_fill if row_num % 2 == 0 else odd_row_fill
        
        if relatorio_tipo == 'carros':
            data = [
                obj.id,
                obj.modelo,
                obj.marca,
                obj.placa,
                obj.ano,
            ]
        if relatorio_tipo == 'agendamentos':
            data = [
                obj.id,
                f"{obj.carro.marca} {obj.carro.modelo} ({obj.carro.placa})",
                str(obj.carro) if obj.carro else "N/A",  # Trata cliente opcional
                obj.data_hora_agenda.strftime('%d/%m/%Y %H:%M'),
                obj.descricao[:50] + '...' if len(obj.descricao) > 50 else obj.descricao,
                obj.responsavel,
                obj.get_status_display()
            ]
            
        
        for col_num, value in enumerate(data, 1):
            col_letter = get_column_letter(col_num)
            cell = ws[f"{col_letter}{row_num}"]
            cell.value = value
            cell.border = border
            cell.fill = row_fill
            if col_num in [1, 4, 7]:  # Colunas para centralizar (ID, Data, Status)
                cell.alignment = center_aligned

    # Ajusta largura das colunas automaticamente
    for column in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2) * 1.2
        ws.column_dimensions[column_letter].width = adjusted_width

    # Configura a resposta
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="relatorio_{relatorio_tipo}.xlsx"'}
    )
    wb.save(response)
    return response


@login_required
def dashboard(request):
    now = timezone.now()
    current_year = now.year
    current_date = now.date()

    # 1. Dados de Veículos
    carros_por_ativo = Carro.objects.values('ativo').annotate(total=Count('id'))
    carros_status = [
        {'status': 'Ativo' if item['ativo'] else 'Inativo', 'total': item['total']}
        for item in carros_por_ativo
    ]

    # 2. Dados de Agendamentos
    agendamentos_por_status = list(Agendamento.objects.values('status').annotate(total=Count('id')))
    
    # 3. Dados Mensais de Agendamentos
    mes_data = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    agendamentos_mes_data = [0] * 12
    agendamentos_por_mes = Agendamento.objects.filter(
        data_hora_agenda__year=current_year
    ).annotate(
        month=ExtractMonth('data_hora_agenda')
    ).values('month').annotate(
        total=Count('id')
    ).order_by('month')

    for item in agendamentos_por_mes:
        month_index = item['month'] - 1  # Janeiro = 0
        if 0 <= month_index < 12:
            agendamentos_mes_data[month_index] = item['total']

    # 4. Métricas Adicionais
    metrics = {
        'total_carros': Carro.objects.count(),
        'carros_ativos': Carro.objects.filter(ativo=True).count(),
        'agendamentos_hoje': Agendamento.objects.filter(
            data_hora_agenda__date=current_date
        ).count(),
        'manutencoes_pendentes': Carro.objects.filter(
            data_proxima_manutencao__lte=current_date
        ).count(),
        'ano_atual': current_year,
    }

    context = {
        'carros_status': carros_status,
        'agendamentos_status': agendamentos_por_status,
        'agendamentos_mes_data': agendamentos_mes_data,
        'mes_data': mes_data,
        **metrics  # Desempacota todas as métricas no contexto
    }
    
    return render(request, 'automovel/dashboard.html', context)


# Relatório fotográfico
logger = logging.getLogger(__name__)

@login_required
def relatorio_fotos_pdf(request, pk):

    agendamento = get_object_or_404(Agendamento, pk=pk)
    
    # Verifica se existe foto principal
    if not agendamento.foto_principal:  
        return HttpResponse("Nenhuma foto disponível para este agendamento", status=404)
    
    context = {
        'agendamento': agendamento,
        'foto_principal_url': os.path.join(settings.MEDIA_ROOT, agendamento.foto_principal.name),
        'MEDIA_URL': settings.MEDIA_URL,
    }
    
    template_path = 'automovel/relatorio_foto_principal_pdf.html'
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="relatorio_foto_{pk}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)

    # Cria o PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF', status=500)
    return response

# Checklist automóvel

@login_required
def checklist(request, agendamento_id, tipo):
    agendamento = get_object_or_404(Agendamento, id=agendamento_id)
    
    if request.method == 'POST':
        form = ChecklistCarroForm(request.POST, request.FILES)
        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.agendamento = agendamento
            checklist.usuario = request.user
            checklist.tipo = tipo
            
            # Atualiza km_inicial com a km atual do carro se for checklist de saída
            if tipo == 'saida':
                checklist.km_inicial = agendamento.carro.km_atual
            
            checklist.save()
            return redirect('detalhes_agendamento', pk=agendamento.id)
    else:
        form = ChecklistCarroForm(initial={
            'tipo': tipo,
            'km_inicial': agendamento.carro.km_atual if tipo == 'saida' else None
        })
    
    return render(request, 'automovel/formulariochecklist.html', {
        'form': form,
        'agendamento': agendamento,
        'tipo': tipo
    })

@login_required
def formulario_checklist(request, agendamento_id):
    agendamento = get_object_or_404(Agendamento, pk=agendamento_id)
    # Sua lógica aqui
    return render(request, 'automovel/formulariochecklist.html', {'agendamento': agendamento})
