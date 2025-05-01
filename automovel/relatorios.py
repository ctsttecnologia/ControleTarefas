from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from openpyxl import Workbook
from .models import Carro, Agendamento
from datetime import datetime
from django.db.models import Count, Q



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

    