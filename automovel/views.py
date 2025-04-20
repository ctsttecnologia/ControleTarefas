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


from .relatorios import gerar_relatorio_pdf, gerar_relatorio_excel
from datetime import datetime, date
from openpyxl import Workbook
from xhtml2pdf import pisa 

from .forms import CarroForm, AgendamentoForm
from .models import Carro, Agendamento

import logging
import os


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
def exportar_pdf(request, tipo):
    return gerar_relatorio_pdf(request, tipo)

def exportar_excel(request, tipo):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"relatorio_{tipo}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb = Workbook()
    ws = wb.active
    
    if tipo == 'carros':
        # Cabeçalhos
        ws.append(['Placa', 'Marca', 'Modelo', 'Ano', 'Cor', 'Status', 'Última Manutenção'])
        
        # Dados
        for carro in Carro.objects.all():
            # Simplifica o status para exportação
            if carro.ativo:
                status = "Manutenção Pendente" if carro.verificar_manutencao_pendente() else "Ativo"
            else:
                status = "Inativo"
                
            ws.append([
                carro.placa,
                carro.marca,
                carro.modelo,
                carro.ano,
                carro.cor,
                status,  # Status simplificado
                carro.data_ultima_manutencao.strftime('%d/%m/%Y') if carro.data_ultima_manutencao else 'N/A'
            ])
    
    # ... (código para outros tipos de relatório)
    
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


