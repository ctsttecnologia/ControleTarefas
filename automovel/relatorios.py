from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from openpyxl import Workbook
from .models import Carro, Agendamento
from datetime import datetime
from django.db.models import Count, Q

def gerar_relatorio_pdf(request, tipo):
    response = HttpResponse(content_type='application/pdf')
    filename = f"relatorio_{tipo}_{datetime.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    
    # Cabeçalho
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 100, f"Relatório de {'Veículos' if tipo == 'carros' else 'Agendamentos'}")
    p.setFont("Helvetica", 12)
    p.drawString(100, height - 130, f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Dados
    if tipo == 'carros':
        dados = Carro.objects.all()
        colunas = ['Placa', 'Marca', 'Modelo', 'Ano', 'Cor', 'Status']
        linhas = [[carro.placa, carro.marca, carro.modelo, carro.ano, carro.cor, carro.status] 
                 for carro in dados]
    else:
        dados = Agendamento.objects.select_related('carro').all()
        colunas = ['Veículo', 'Data', 'Serviço', 'Responsável', 'Status']
        linhas = [[f"{ag.carro.placa} ({ag.carro.modelo})", 
                  ag.data_hora_agenda.strftime('%d/%m/%Y %H:%M'),
                  ag.descricao[:30] + '...' if len(ag.descricao) > 30 else ag.descricao,
                  ag.responsavel,
                  ag.get_status_display()] 
                 for ag in dados]
    
    # Tabela
    data = [colunas] + linhas
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    table.wrapOn(p, width - 200, height - 200)
    table.drawOn(p, 100, height - 350)
    
    p.showPage()
    p.save()
    return response

def gerar_relatorio_excel(request, tipo):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"relatorio_{tipo}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb = Workbook()
    ws = wb.active
    ws.title = tipo.capitalize()
    
    if tipo == 'carros':
        dados = Carro.objects.all()
        ws.append(['Placa', 'Marca', 'Modelo', 'Ano', 'Cor', 'Status', 'Última Manutenção'])
        for carro in dados:
            ws.append([
                carro.placa,
                carro.marca,
                carro.modelo,
                carro.ano,
                carro.cor,
                carro.status,
                carro.data_ultima_manutencao.strftime('%d/%m/%Y') if carro.data_ultima_manutencao else 'N/A'
            ])
    else:
        dados = Agendamento.objects.select_related('carro').all()
        ws.append(['Veículo', 'Placa', 'Data', 'Serviço', 'Responsável', 'Status', 'KM Inicial'])
        for ag in dados:
            ws.append([
                f"{ag.carro.marca} {ag.carro.modelo}",
                ag.carro.placa,
                ag.data_hora_agenda.strftime('%d/%m/%Y %H:%M'),
                ag.descricao,
                ag.responsavel,
                ag.get_status_display(),
                ag.km_inicial
            ])
    
    wb.save(response)
    return response

    