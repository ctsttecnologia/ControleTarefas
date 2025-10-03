
from django.http import HttpResponse
from openpyxl import Workbook
from .models import Carro, Agendamento
from datetime import datetime

def gerar_relatorio_excel(request, tipo):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"relatorio_{tipo}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb = Workbook()
    ws = wb.active
    ws.title = tipo.capitalize()
    
    # Busca os dados já filtrados pelo manager
    filial_qs = Carro.objects.for_request(request) if tipo == 'carros' else Agendamento.objects.for_request(request)
    
    if tipo == 'carros':
        dados = filial_qs.filter(ativo=True)
        ws.append(['Placa', 'Marca', 'Modelo', 'Ano', 'Cor', 'Disponível', 'Última Manutenção'])
        for carro in dados:
            # MUDANÇA: trocado 'carro.status' por um campo que existe
            status_carro = "Sim" if carro.disponivel else "Não"
            ws.append([
                carro.placa, carro.marca, carro.modelo, carro.ano, carro.cor,
                status_carro,
                carro.data_ultima_manutencao.strftime('%d/%m/%Y') if carro.data_ultima_manutencao else 'N/A'
            ])
    else: # Agendamentos
        dados = filial_qs.select_related('carro')
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
    