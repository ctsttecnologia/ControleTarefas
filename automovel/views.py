# automovel/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import IntegrityError
from django.utils import timezone 
from django.db.models import Count, Q, Sum, Case, When, Value
from django.http import HttpResponse, JsonResponse, HttpResponseServerError
from django.db.models.functions import ExtractMonth
from django.template.loader import get_template, render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.views.generic import UpdateView
from django.urls import reverse_lazy

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
import openpyxl
import logging
import os
import io
from io import BytesIO
import json

from .relatorios import gerar_relatorio_excel
from datetime import datetime, date
from .forms import CarroForm, AgendamentoForm, ChecklistCarroForm, AssinaturaForm
from .models import Carro, Agendamento, Checklist_Carro

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import xml.etree.ElementTree as ET
from docx.enum.table import WD_ALIGN_VERTICAL


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
                
                # Define o responsável se não foi preenchido
                if not agendamento.responsavel:
                    agendamento.responsavel = request.user.get_full_name() or request.user.username
                
                # Garante que os campos booleanos são processados corretamente
                agendamento.pedagio = form.cleaned_data.get('pedagio', False)
                agendamento.abastecimento = form.cleaned_data.get('abastecimento', False)
                agendamento.cancelar_agenda = form.cleaned_data.get('cancelar_agenda', False)
                
                # Se for cancelado, verifica motivo
                if agendamento.cancelar_agenda or agendamento.status == 'cancelado':
                    if not form.cleaned_data.get('motivo_cancelamento'):
                        form.add_error('motivo_cancelamento', 'Motivo é obrigatório para cancelamentos')
                        return render(request, 'automovel/agendamento_form.html', {'form': form})
                
                agendamento.save()
                messages.success(request, 'Agendamento criado com sucesso!')
                return redirect('automovel:lista_agendamentos')
            
            except IntegrityError as e:
                messages.error(request, f'Erro ao salvar: {str(e)}')
                logger.error(f"IntegrityError: {str(e)}")
                return render(request, 'automovel/agendamento_form.html', {'form': form})
            except Exception as e:
                messages.error(request, f'Erro inesperado: {str(e)}')
                logger.error(f"Exception: {str(e)}")
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
class AdicionarAssinaturaView(UpdateView):
    model = Agendamento
    form_class = AssinaturaForm
    template_name = 'automovel/adicionar_assinatura.html'
    
    def get_success_url(self):
        return reverse_lazy('automovel:lista_agendamentos')
    
    def form_valid(self, form):
        form.instance.responsavel = self.request.user
        return super().form_valid(form)

def checklist_carro(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    # Lógica do checklist de saída
    return render(request, 'automovel/checklist_carro.html', {'agendamento': agendamento})

@login_required
def agendamento_fotos(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    return render(request, 'automovel/agendamento_fotos.html', {'agendamento': agendamento})


#RELATÓRIO
@login_required
def relatorios(request):

    # Busca checklists com agendamentos e carros relacionados
    checklists = Checklist_Carro.objects.select_related(
        'agendamento',
        'agendamento__carro'
    ).filter(
        agendamento__isnull=False
    ).order_by('-data_criacao')
    
    # Verifica se há dados para debug
    print(f"Checklists encontrados: {checklists.count()}")  # Debug
    
    return render(request, 'automovel/relatorios.html', {
        'checklists': checklists
    })

    # Mostra todos os checklists, mesmo sem agendamento (para debug)
    checklists = Checklist_Carro.objects.all().order_by('-data_criacao')
    return render(request, 'automovel/relatorios.html', {'checklists': checklists})

# view exportar_world
@login_required
def exportar_word(request, relatorio_tipo):
    try:
        if relatorio_tipo == 'carros':
            queryset = Carro.objects.all().order_by('marca', 'modelo')
            filename = 'relatorio_carros.docx'
            titulo = "Relatório de Veículos"
        elif relatorio_tipo == 'agendamentos':
            queryset = Agendamento.objects.select_related('carro').all().order_by('-data_hora_agenda')
            filename = 'relatorio_agendamentos.docx'
            titulo = "Relatório de Agendamentos"
        else:
            return HttpResponse("Tipo de relatório inválido", status=400)

        # Cria um novo documento Word
        document = Document()
        
        # Adiciona título
        title = document.add_heading(titulo, level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Adiciona data de emissão
        document.add_paragraph(f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        document.add_paragraph()
        
        # Cria tabela
        table = document.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        
        # Cabeçalhos
        hdr_cells = table.rows[0].cells
        if relatorio_tipo == 'carros':
            headers = ['ID', 'Marca', 'Modelo', 'Placa', 'Ano']
        else:
            headers = ['ID', 'Veículo', 'Data', 'Responsável', 'Status']
        
        for i, header in enumerate(headers):
            hdr_cells[i].text = header
            hdr_cells[i].paragraphs[0].runs[0].font.bold = True
        
        # Adiciona dados
        for obj in queryset:
            row_cells = table.add_row().cells
            if relatorio_tipo == 'carros':
                row_cells[0].text = str(obj.id)
                row_cells[1].text = obj.marca
                row_cells[2].text = obj.modelo
                row_cells[3].text = obj.placa
                row_cells[4].text = str(obj.ano)
            else:
                row_cells[0].text = str(obj.id)
                row_cells[1].text = f"{obj.carro.marca} {obj.carro.modelo}" if obj.carro else "N/A"
                row_cells[2].text = obj.data_hora_agenda.strftime('%d/%m/%Y %H:%M') if obj.data_hora_agenda else "N/A"
                row_cells[3].text = obj.responsavel or "N/A"
                row_cells[4].text = obj.get_status_display() if hasattr(obj, 'get_status_display') else obj.status

        # Configura a resposta
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        document.save(response)
        
        return response

    except Exception as e:
        return HttpResponse(f"Erro ao gerar relatório Word: {str(e)}", status=500)
# Relatório em xml
@login_required
def exportar_xml(request, relatorio_tipo):
    try:
        if relatorio_tipo == 'carros':
            queryset = Carro.objects.all().order_by('marca', 'modelo')
            root = ET.Element('RelatorioCarros')
        elif relatorio_tipo == 'agendamentos':
            queryset = Agendamento.objects.select_related('carro').all().order_by('-data_hora_agenda')
            root = ET.Element('RelatorioAgendamentos')
        else:
            return HttpResponse("Tipo de relatório inválido", status=400)

        # Adiciona metadados
        metadata = ET.SubElement(root, 'Metadados')
        ET.SubElement(metadata, 'DataEmissao').text = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        ET.SubElement(metadata, 'TotalRegistros').text = str(queryset.count())

        # Adiciona dados
        dados = ET.SubElement(root, 'Dados')
        
        for obj in queryset:
            if relatorio_tipo == 'carros':
                registro = ET.SubElement(dados, 'Carro')
                ET.SubElement(registro, 'ID').text = str(obj.id)
                ET.SubElement(registro, 'Marca').text = str(obj.marca)  # Convertendo para string
                ET.SubElement(registro, 'Modelo').text = str(obj.modelo)
                ET.SubElement(registro, 'Placa').text = str(obj.placa)
                ET.SubElement(registro, 'Ano').text = str(obj.ano)
                # Para campos de escolha, use get_FOO_display() ou force_str
                ET.SubElement(registro, 'Status').text = str(obj.get_status_display() if hasattr(obj, 'get_status_display') else obj.status)
            else:
                registro = ET.SubElement(dados, 'Agendamento')
                ET.SubElement(registro, 'ID').text = str(obj.id)
                ET.SubElement(registro, 'Veiculo').text = str(f"{obj.carro.marca} {obj.carro.modelo}" if obj.carro else "N/A")
                ET.SubElement(registro, 'DataHora').text = obj.data_hora_agenda.strftime('%Y-%m-%dT%H:%M:%S') if obj.data_hora_agenda else ""
                ET.SubElement(registro, 'Responsavel').text = str(obj.responsavel or "N/A")
                ET.SubElement(registro, 'Status').text = str(obj.get_status_display())

        # Cria um objeto ElementTree
        tree = ET.ElementTree(root)
        
        # Cria um buffer de memória para o XML
        xml_buffer = BytesIO()
        tree.write(xml_buffer, encoding='utf-8', xml_declaration=True)
        
        # Configura a resposta
        response = HttpResponse(xml_buffer.getvalue(), content_type='application/xml')
        response['Content-Disposition'] = f'attachment; filename=relatorio_{relatorio_tipo}.xml'
        
        return response

    except Exception as e:
        logger.error(f"Erro ao gerar relatório XML: {str(e)}", exc_info=True)
        return HttpResponse(f"Erro ao gerar relatório XML: {str(e)}", status=500)

@login_required
def exportar_excel(request, relatorio_tipo):
    try:
        if relatorio_tipo == 'carros':
            queryset = Carro.objects.all().order_by('marca', 'modelo')
            titulo = "Relatório de Veículos"
            colunas = ["ID", "Modelo", "Marca", "Placa", "Ano", "Cor", "Status"]
        elif relatorio_tipo == 'agendamentos':
            queryset = Agendamento.objects.select_related('carro').all().order_by('-data_hora_agenda')
            titulo = "Relatório de Agendamentos"
            colunas = ["ID", "Veículo", "Data", "Serviço", "Responsável", "Status"]
        else:
            return HttpResponse("Tipo de relatório inválido", status=400)

        wb = Workbook()
        ws = wb.active
        ws.title = titulo[:31]

        # Adiciona cabeçalhos
        for col_num, header in enumerate(colunas, 1):
            col_letter = get_column_letter(col_num)
            ws[f"{col_letter}1"] = header
            ws[f"{col_letter}1"].font = Font(bold=True)

        # Adiciona dados
        for row_num, obj in enumerate(queryset, 2):
            if relatorio_tipo == 'carros':
                ws[f"A{row_num}"] = obj.id
                ws[f"B{row_num}"] = obj.modelo
                ws[f"C{row_num}"] = obj.marca
                ws[f"D{row_num}"] = obj.placa
                ws[f"E{row_num}"] = obj.ano
                ws[f"F{row_num}"] = obj.cor
                ws[f"G{row_num}"] = str(obj.status)  # Convertendo para string
            else:
                ws[f"A{row_num}"] = obj.id
                ws[f"B{row_num}"] = f"{obj.carro.marca} {obj.carro.modelo}" if obj.carro else "N/A"
                ws[f"C{row_num}"] = obj.data_hora_agenda.strftime('%d/%m/%Y %H:%M') if obj.data_hora_agenda else "N/A"
                ws[f"D{row_num}"] = obj.descricao[:50] + '...' if obj.descricao else "N/A"
                ws[f"E{row_num}"] = obj.responsavel or "N/A"
                ws[f"F{row_num}"] = str(obj.status)  # Usando o valor bruto ao invés de get_status_display()

        # Ajusta largura das colunas
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

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="relatorio_{relatorio_tipo}.xlsx"'
        wb.save(response)
        return response

    except Exception as e:
        logger.error(f"Erro ao gerar Excel: {str(e)}")
        return HttpResponse(f"Erro ao gerar relatório Excel: {str(e)}", status=500)

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

from django.core.exceptions import ObjectDoesNotExist


# Checklist automóvel

@login_required
def checklist(request, agendamento_id, tipo):
    agendamento = get_object_or_404(Agendamento, id=agendamento_id)
    
    if request.method == 'POST':
        form = ChecklistCarroForm(request.POST, request.FILES)
        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.agendamento = agendamento
            checklist.tipo = tipo
            checklist.usuario = request.user
            checklist.save()
            return redirect('automovel:detalhes_agendamento', pk=agendamento_id)
    else:
        form = ChecklistCarroForm(initial={
            'tipo': tipo,
            'km_inicial': agendamento.km_inicial if tipo == 'saida' else None
        })
    
    return render(request, 'automovel/checklist_form.html', {
        'form': form,
        'agendamento': agendamento,
        'tipo': tipo
    })

@login_required
def formulario_checklist(request, agendamento_id):
    agendamento = get_object_or_404(Agendamento, pk=agendamento_id)
    # Sua lógica aqui
    return render(request, 'automovel/checklist_carro.html', {'agendamento': agendamento})

class AdicionarAssinaturaView(UpdateView):
    model = Agendamento
    form_class = AssinaturaForm
    template_name = 'automovel/adicionar_assinatura.html'
    
    def get_success_url(self):
        messages.success(self.request, 'Assinatura registrada com sucesso!')
        return reverse_lazy('automovel:lista_agendamentos')
    
    def form_valid(self, form):
        form.instance.status = 'concluido'
        return super().form_valid(form)

@login_required
def checklist_carro(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    
    if request.method == 'POST':
        form = ChecklistCarroForm(request.POST, request.FILES)
        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.agendamento = agendamento
            checklist.usuario = request.user
            checklist.save()
            
            # Atualiza status do agendamento
            agendamento.status = 'concluido'
            agendamento.save()
            
            messages.success(request, 'Checklist salvo com sucesso!')
            return redirect('automovel:lista_agendamentos')
    else:
        form = ChecklistCarroForm(initial={
            'km_inicial': agendamento.km_inicial,
            'km_final': agendamento.km_final
        })
    
    return render(request, 'automovel/checklist_carro.html', {
        'form': form,
        'agendamento': agendamento,
       
    })

# Relatório ckecklist
@login_required
def relatorio_checklist_word(request, checklist_id):
    try:
        checklist = Checklist_Carro.objects.get(id=checklist_id)
        agendamento = checklist.agendamento
        carro = agendamento.carro
        
        # Criar um novo documento Word
        document = Document()
        
        # Configuração básica do documento
        section = document.sections[0]
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        
        # Cabeçalho
        header = document.add_heading('RELATÓRIO DE CHECKLIST VEICULAR', level=1)
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        header.runs[0].font.color.rgb = RGBColor(0, 0, 0)
        header.runs[0].font.size = Pt(14)
        header.runs[0].font.bold = True
        
        # Informações básicas
        document.add_paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        document.add_paragraph(f"Tipo de Checklist: {checklist.get_tipo_display()}")
        document.add_paragraph(f"Veículo: {carro.marca} {carro.modelo} - {carro.placa}")
        document.add_paragraph(f"Agendamento: #{agendamento.id} - {agendamento.funcionario}")
        document.add_paragraph(f"Quilometragem Inicial: {checklist.km_inicial}")
        if checklist.km_final:
            document.add_paragraph(f"Quilometragem Final: {checklist.km_final}")
        
        # Adicionar tabela de itens do checklist
        document.add_paragraph("\nItens do Checklist:", style='Heading 2')
        
        table = document.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        
        # Cabeçalhos da tabela
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Item'
        hdr_cells[1].text = 'Status'
        hdr_cells[2].text = 'Observações'
        
        # Configurar estilo dos cabeçalhos
        for cell in hdr_cells:
            cell.paragraphs[0].runs[0].font.bold = True
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        
        # Adicionar itens do checklist
        itens = [
            ('Frontal', checklist.revisao_frontal_status, checklist.coordenadas_avaria_frontal),
            ('Traseira', checklist.revisao_trazeira_status, checklist.coordenadas_avaria_trazeira),
            ('Lado Motorista', checklist.revisao_lado_motorista_status, checklist.coordenadas_avaria_lado_motorista),
            ('Lado Passageiro', checklist.revisao_lado_passageiro_status, checklist.coordenadas_lado_passageiro),
        ]
        
        for item in itens:
            row_cells = table.add_row().cells
            row_cells[0].text = item[0]
            row_cells[1].text = item[1]
            row_cells[2].text = str(item[2]) if item[2] else '-'
        
        # Observações gerais
        if checklist.observacoes_gerais:
            document.add_paragraph("\nObservações Gerais:", style='Heading 2')
            document.add_paragraph(checklist.observacoes_gerais)
        
        # Assinatura
        document.add_paragraph("\nResponsável:", style='Heading 2')
        document.add_paragraph(f"Nome: {checklist.usuario.get_full_name()}")
        document.add_paragraph(f"Data: {checklist.data_criacao.strftime('%d/%m/%Y %H:%M')}")
        
        # Salvar o documento em um buffer
        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)
        
        # Configurar a resposta HTTP
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename=relatorio_checklist_{checklist_id}.docx'
        
        return response
        
    except Exception as e:
        return HttpResponse(f"Erro ao gerar relatório: {str(e)}", status=500)

@login_required
def relatorio_fotografico_word(request, agendamento_id):
    try:
        agendamento = get_object_or_404(Agendamento, id=agendamento_id)
        carro = agendamento.carro
        fotos = agendamento.fotos.all()
        
        # Criar um novo documento Word
        document = Document()
        
        # Configuração básica do documento
        section = document.sections[0]
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        
        # Cabeçalho
        header = document.add_heading('RELATÓRIO FOTOGRÁFICO', level=1)
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        header.runs[0].font.color.rgb = RGBColor(0, 0, 0)
        header.runs[0].font.size = Pt(14)
        header.runs[0].font.bold = True
        
        # Informações básicas
        document.add_paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        document.add_paragraph(f"Veículo: {carro.marca} {carro.modelo} - {carro.placa}")
        document.add_paragraph(f"Agendamento: #{agendamento.id}")
        document.add_paragraph(f"Responsável: {agendamento.responsavel or 'N/A'}")
        if agendamento.data_hora_agenda:
            document.add_paragraph(f"Data/Hora: {agendamento.data_hora_agenda.strftime('%d/%m/%Y %H:%M')}")
        
        # Adicionar fotos
        if fotos.exists():
            document.add_paragraph("\nFotos do Veículo:", style='Heading 2')
            
            for foto in fotos:
                # Adicionar título da foto
                document.add_paragraph(f"Foto: {foto.observacao or 'Sem descrição'}", style='Heading 3')
                
                try:
                    # Adicionar a imagem ao documento
                    img_path = foto.imagem.path
                    document.add_picture(img_path, width=Inches(5))
                    
                    # Centralizar a imagem
                    last_paragraph = document.paragraphs[-1]
                    last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    
                except Exception as e:
                    logger.error(f"Erro ao carregar imagem {foto.id}: {str(e)}")
                    document.add_paragraph(f"[Erro ao carregar esta imagem]")
        
        else:
            document.add_paragraph("\nNenhuma foto encontrada para este agendamento.")
        
        # Salvar o documento em um buffer
        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)
        
        # Configurar a resposta HTTP
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename=relatorio_fotografico_{agendamento_id}.docx'
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório fotográfico: {str(e)}", exc_info=True)
        return HttpResponse(f"Erro ao gerar relatório: {str(e)}", status=500)
