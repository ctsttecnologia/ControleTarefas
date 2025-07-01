# tarefas/services.py

import io
import csv
from datetime import datetime
from collections import Counter

from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.db.models import Avg

# Importe o WeasyPrint e o Document do python-docx
from weasyprint import HTML
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH



def preparar_contexto_relatorio(queryset):
    """Prepara o dicionário de contexto com dados agregados (versão de depuração final)."""
    status_map = {choice[0]: choice[1] for choice in queryset.model.STATUS_CHOICES}
    prioridade_map = {choice[0]: choice[1] for choice in queryset.model.PRIORIDADE_CHOICES}
    total_tarefas = queryset.count()
 
    # ... (A lógica de status continua a mesma) ...
    status_data = []
    if total_tarefas > 0:
        for status_key, status_label in status_map.items():
            # ...
            status_data.append({
                'label': str(status_label), 'count': Counter(queryset.values_list('status', flat=True)).get(status_key, 0),
                'percent': round((Counter(queryset.values_list('status', flat=True)).get(status_key, 0) / total_tarefas * 100), 2),
                'key': status_key, 'avg_duration': None
            })

    # --- INÍCIO DA DEPURAÇÃO DE PRIORIDADE ---
    #print("\n--- INÍCIO DA DEPURAÇÃO DE PRIORIDADE ---")
    
    # DEBUG 1: Verificando a fonte de dados
    choices_list = queryset.model.PRIORIDADE_CHOICES
    #print("DEBUG 1 (Fonte): A lista de CHOICES é:", choices_list)

    prioridade_counts = Counter(queryset.values_list('prioridade', flat=True))
    prioridade_data = []
    
    if choices_list:
        for prioridade_key, prioridade_label in choices_list:
            count = prioridade_counts.get(prioridade_key, 0)
            percent = (count / total_tarefas * 100) if total_tarefas > 0 else 0
            prioridade_data.append({
                'label': str(prioridade_label), 'count': count,
                'percent': round(percent, 2), 'key': prioridade_key
            })

    # DEBUG 2: Verificando o resultado do loop
    #print("DEBUG 2 (Resultado do Loop): A lista prioridade_data é:", prioridade_data)

    # Montagem do contexto
    context = {
        'tarefas': queryset,
        'total_tarefas': total_tarefas,
        'status_data': sorted(status_data, key=lambda x: x['label']),
        'prioridade_data': prioridade_data,  # ESTA É A VERSÃO CORRIGIDA. VERIFIQUE SE A SUA ESTÁ IGUAL.
        'status_map': status_map,
        'prioridade_map': prioridade_map,
        'now': datetime.now(),
        'logo_path': finders.find('imagens/logocetest.png'),
    }

    # DEBUG 3: Verificando o valor final no contexto
    #print("DEBUG 3 (Contexto Final): O valor em context['prioridade_data'] é:", context.get('prioridade_data'))
    #print("--- FIM DA DEPURAÇÃO ---\n")
    
    return context

def gerar_pdf_relatorio(context):
    """Gera um relatório em PDF."""
    template = get_template('tarefas/relatorio_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    filename = f"relatorio_tarefas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf(response)
    return response

def gerar_csv_relatorio(context):
    """Gera um relatório em CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"relatorio_tarefas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Título', 'Responsável', 'Status', 'Prioridade', 'Projeto',
        'Data Criação', 'Prazo', 'Duração Prevista', 'Tempo Gasto',
        'Lembrete (Dias)', 'Data Lembrete'
    ])

    status_map = context['status_map']
    prioridade_map = context['prioridade_map']
    for tarefa in context['tarefas']:
        writer.writerow([
            tarefa.titulo,
            tarefa.responsavel.username if tarefa.responsavel else '-',
            status_map.get(tarefa.status, tarefa.status),
            prioridade_map.get(tarefa.prioridade, tarefa.prioridade),
            tarefa.projeto if tarefa.projeto else '-',
            tarefa.data_criacao.strftime('%d/%m/%Y %H:%M'),
            tarefa.prazo.strftime('%d/%m/%Y %H:%M') if tarefa.prazo else '-',
            str(tarefa.duracao_prevista) if tarefa.duracao_prevista else '-',
            str(tarefa.tempo_gasto) if tarefa.tempo_gasto else '-',
            tarefa.dias_lembrete if tarefa.dias_lembrete else '-',
            tarefa.data_lembrete.strftime('%d/%m/%Y') if tarefa.data_lembrete else '-',
        ])
    return response

def gerar_docx_relatorio(context):
    """Gera um relatório em DOCX (Word) com a lógica de tabela corrigida."""
    document = Document()
    
    # --- CABEÇALHO ---
    if context.get('logo_path'):
        try:
            document.add_picture(context['logo_path'], width=Inches(1.5))
        except Exception:
            document.add_paragraph('Logotipo não encontrado.')

    p = document.add_paragraph()
    p.add_run('Relatório de Tarefas').bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].font.size = Pt(16)
    document.add_paragraph(f"Gerado em: {context['now'].strftime('%d/%m/%Y %H:%M')}", style='Intense Quote')

    # --- ANÁLISES (OPCIONAL) ---
    document.add_heading('Resumo por Status', level=1)
    for item in context['status_data']:
        document.add_paragraph(f"{item['label']}: {item['count']} ({item['percent']}%)", style='List Bullet')

    # --- TABELA DE DETALHES (LÓGICA CORRIGIDA) ---
    document.add_heading('Detalhes das Tarefas', level=1)
    
    # Define os cabeçalhos da tabela
    headers = [
        'Título', 'Responsável', 'Status', 'Prioridade', 'Projeto', 'Criação', 'Prazo'
    ]
    # Cria a tabela com 1 linha (cabeçalho) e o número correto de colunas
    table = document.add_table(rows=1, cols=len(headers), style='Table Grid')

    # Preenche a primeira linha com os cabeçalhos
    hdr_cells = table.rows[0].cells
    for i, header_text in enumerate(headers):
        hdr_cells[i].text = header_text
        hdr_cells[i].paragraphs[0].runs[0].bold = True

    # Preenche o resto da tabela com os dados das tarefas
    status_map = context['status_map']
    prioridade_map = context['prioridade_map']
    
    for tarefa in context['tarefas']:
        row_cells = table.add_row().cells
        row_cells[0].text = tarefa.titulo
        row_cells[1].text = tarefa.responsavel.username if tarefa.responsavel else '-'
        row_cells[2].text = status_map.get(tarefa.status, tarefa.status)
        row_cells[3].text = prioridade_map.get(tarefa.prioridade, tarefa.prioridade)
        row_cells[4].text = tarefa.projeto if tarefa.projeto else '-'
        row_cells[5].text = tarefa.data_criacao.strftime('%d/%m/%Y')
        row_cells[6].text = tarefa.prazo.strftime('%d/%m/%Y') if tarefa.prazo else '-'

    # --- SALVA E RETORNA O ARQUIVO ---
    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    filename = f"relatorio_tarefas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response