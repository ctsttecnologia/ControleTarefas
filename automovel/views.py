from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.template.loader import get_template

from datetime import datetime, timedelta
from openpyxl import Workbook
from docx import Document

from .models import Carro, Agendamento, Checklist, Foto
from .forms import CarroForm, AgendamentoForm, ChecklistForm, FotoForm
from io import BytesIO


class DashboardView(LoginRequiredMixin, ListView):  
    template_name = 'automovel/dashboard.html'
    context_object_name = 'carros'
    
    def get_queryset(self):
        return Carro.objects.filter(ativo=True).order_by('-id')[:5]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = datetime.now().date()
        
        context['carros_disponiveis'] = Carro.objects.filter(disponivel=True, ativo=True).count()
        context['agendamentos_hoje'] = Agendamento.objects.filter(
            data_hora_agenda__date=hoje,
            status='agendado'
        ).count()
        context['manutencao_proxima'] = Carro.objects.filter(
            data_proxima_manutencao__lte=hoje + timedelta(days=7),
            data_proxima_manutencao__gte=hoje,
            ativo=True
        ).count()
        context['ultimos_agendamentos'] = Agendamento.objects.order_by('-data_hora_agenda')[:5]
        
        return context

class CarroListView(LoginRequiredMixin, ListView):
    model = Carro
    template_name = 'automovel/carro_list.html'
    context_object_name = 'carros'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        
        if search:
            queryset = queryset.filter(
                Q(placa__icontains=search) |
                Q(modelo__icontains=search) |
                Q(marca__icontains=search)
            )
        
        return queryset.filter(ativo=True)

class CarroCreateView(LoginRequiredMixin, CreateView):
    model = Carro
    form_class = CarroForm
    template_name = 'automovel/carro_form.html'
    success_url = reverse_lazy('automovel:carro_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Carro cadastrado com sucesso!')
        return super().form_valid(form)

class CarroUpdateView(LoginRequiredMixin, UpdateView):
    model = Carro
    form_class = CarroForm
    template_name = 'automovel/carro_form.html'
    success_url = reverse_lazy('automovel:carro_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Carro atualizado com sucesso!')
        return super().form_valid(form)

class CarroDetailView(LoginRequiredMixin, DetailView):
    model = Carro
    template_name = 'automovel/carro_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agendamentos'] = Agendamento.objects.filter(carro=self.object).order_by('-data_hora_agenda')[:5]
        return context

class AgendamentoListView(LoginRequiredMixin, ListView):
    model = Agendamento
    template_name = 'automovel/agendamento_list.html'
    context_object_name = 'agendamentos'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')
        
        if status:
            queryset = queryset.filter(status=status)
        
        if search:
            queryset = queryset.filter(
                Q(funcionario__icontains=search) |
                Q(carro__placa__icontains=search)
            )
        
        return queryset.order_by('-data_hora_agenda')

class AgendamentoCreateView(LoginRequiredMixin, CreateView):
    model = Agendamento
    form_class = AgendamentoForm
    template_name = 'automovel/agendamento_form.html'
    success_url = reverse_lazy('automovel:agendamento_list')
    
    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, 'Agendamento criado com sucesso!')
        return super().form_valid(form)

class AgendamentoDetailView(LoginRequiredMixin, DetailView):
    model = Agendamento
    template_name = 'automovel/agendamento_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['checklists'] = Checklist.objects.filter(agendamento=self.object)
        context['fotos'] = Foto.objects.filter(agendamento=self.object)
        return context
def agendamento_detail(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    checklist_saida = Checklist.objects.filter(agendamento=agendamento, tipo='saida').first()
    checklist_retorno = Checklist.objects.filter(agendamento=agendamento, tipo='retorno').first()
    context = {
        'agendamento': agendamento,
        'checklist_saida': checklist_saida,
        'checklist_retorno': checklist_retorno,
    }
    return render(request, 'automovel/agendamento_detail.html', context)

class ChecklistCreateView(LoginRequiredMixin, CreateView):
    model = Checklist
    form_class = ChecklistForm
    template_name = 'automovel/checklist_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['data_hora'] = timezone.now()
        agendamento_id = self.request.GET.get('agendamento')
        if agendamento_id:
            initial['agendamento'] = agendamento_id
        return initial

    def get_success_url(self):
        return reverse('automovel:agendamento_detail', kwargs={'pk': self.object.agendamento.id})

    def form_valid(self, form):
        messages.success(self.request, 'Checklist criado com sucesso!')
        return super().form_valid(form)
    
    # Adicione também estes métodos para garantir que o agendamento seja passado para o template
    def get_initial(self):
        initial = super().get_initial()
        agendamento_id = self.request.GET.get('agendamento')
        if agendamento_id:
            initial['agendamento'] = agendamento_id
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agendamento_id = self.request.GET.get('agendamento')
        if agendamento_id:
            try:
                from .models import Agendamento  # Importe seu modelo Agendamento
                context['agendamento'] = Agendamento.objects.get(pk=agendamento_id)
            except Agendamento.DoesNotExist:
                pass
        return context
    
    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, 'Checklist criado com sucesso!')
        return super().form_valid(form)

def checklist_create(request, agendamento_id):
    agendamento = get_object_or_404(Agendamento, pk=agendamento_id)
    
    if request.method == 'POST':
        form = ChecklistForm(request.POST, request.FILES)
        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.agendamento = agendamento
            checklist.usuario = request.user
            checklist.save()

            # Verifica se é para finalizar
            if 'finalizar' in request.POST and checklist.tipo == 'retorno':
                agendamento.status = 'finalizado'
                agendamento.save()
                messages.success(request, 'Checklist de retorno salvo e agendamento finalizado com sucesso!')
            else:
                agendamento.status = 'em_andamento'
                agendamento.save()
                messages.success(request, 'Checklist salvo com sucesso!')
                
            return redirect('automovel:agendamento_detail', agendamento.id)
        else:
            form = ChecklistForm(initial={
                'agendamento': agendamento,
                'usuario': request.user,
                'tipo': 'retorno' if agendamento.status == 'em_andamento' else 'saida'
            })
        
        # Adiciona URLs das fotos existentes ao contexto do formulário
    if form.instance.pk:
        for field in ['foto_frontal', 'foto_trazeira', 'foto_lado_motorista', 'foto_lado_passageiro']:
            if getattr(form.instance, field):
                form.fields[field].widget.attrs['data-existing-file'] = getattr(form.instance, field).url
    
            return render(request, 'automovel/checklist_form.html', {
            'form': form,
            'agendamento': agendamento
        })
            
            # Atualiza status do agendamento
            if checklist.tipo == 'saida':
                agendamento.status = 'em_andamento'
                agendamento.save()
            elif checklist.tipo == 'retorno':
                agendamento.status = 'finalizado'
                agendamento.save()
            
            messages.success(request, 'Checklist salvo com sucesso!')
            return redirect('automovel:agendamento_detail', agendamento.id)
    else:
        form = ChecklistForm(initial={'agendamento': agendamento, 'usuario': request.user})
    
    return render(request, 'automovel/checklist_form.html', {
        'form': form,
        'agendamento': agendamento
    })        

def export_checklist_word(request, pk):
    checklist = get_object_or_404(Checklist, pk=pk)
    
    # Cria um novo documento Word
    document = Document()
    
    # Adiciona título
    document.add_heading(f'Checklist de Veículo - {checklist.get_tipo_display()}', 0)
    
    # Informações básicas
    document.add_paragraph(f'Data/Hora: {checklist.data_hora.strftime("%d/%m/%Y %H:%M")}')
    document.add_paragraph(f'Veículo: {checklist.agendamento.carro.modelo} - Placa: {checklist.agendamento.carro.placa}')
    document.add_paragraph(f'Motorista: {checklist.agendamento.funcionario.nome}')
    document.add_paragraph(f'KM Inicial: {checklist.km_inicial} | KM Final: {checklist.km_final}')
    
    # Adiciona tabela de vistoria
    document.add_heading('Vistoria do Veículo', level=1)
    table = document.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    
    # Cabeçalho da tabela
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Item'
    hdr_cells[1].text = 'Status'
    hdr_cells[2].text = 'Observações'
    
    # Adiciona itens da vistoria
    items = [
        ('Parte Frontal', checklist.get_revisao_frontal_status_display()),
        ('Parte Trazeira', checklist.get_revisao_trazeira_status_display()),
        ('Lado Motorista', checklist.get_revisao_lado_motorista_status_display()),
        ('Lado Passageiro', checklist.get_revisao_lado_passageiro_status_display()),
    ]
    
    for item, status in items:
        row_cells = table.add_row().cells
        row_cells[0].text = item
        row_cells[1].text = status
        row_cells[2].text = checklist.observacoes_gerais if checklist.observacoes_gerais else 'N/A'
    
    # Adiciona assinatura
    document.add_heading('Assinatura', level=1)
    document.add_paragraph('Responsável pela vistoria: _________________________________________')
    
    # Salva o documento em um buffer
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    
    # Cria a resposta
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename=checklist_{checklist.id}_{checklist.tipo}.docx'
    
    return response

def export_checklist_excel(request, pk):
    checklist = get_object_or_404(Checklist, pk=pk)
    
    # Cria uma nova planilha Excel
    wb = Workbook()
    ws = wb.active
    ws.title = f"Checklist {checklist.tipo}"
    
    # Adiciona cabeçalho
    ws['A1'] = f'Checklist de Veículo - {checklist.get_tipo_display()}'
    ws.merge_cells('A1:D1')
    
    # Informações básicas
    ws.append(['Data/Hora:', checklist.data_hora.strftime("%d/%m/%Y %H:%M")])
    ws.append(['Veículo:', f'{checklist.agendamento.carro.modelo} - Placa: {checklist.agendamento.carro.placa}'])
    ws.append(['Motorista:', checklist.agendamento.funcionario.nome])
    ws.append(['KM Inicial:', checklist.km_inicial])
    ws.append(['KM Final:', checklist.km_final])
    ws.append([])  # Linha vazia
    
    # Adiciona tabela de vistoria
    ws.append(['Vistoria do Veículo'])
    ws.merge_cells('A6:D6')
    
    # Cabeçalho da tabela
    ws.append(['Item', 'Status', 'Observações'])
    
    # Adiciona itens da vistoria
    items = [
        ('Parte Frontal', checklist.get_revisao_frontal_status_display()),
        ('Parte Trazeira', checklist.get_revisao_trazeira_status_display()),
        ('Lado Motorista', checklist.get_revisao_lado_motorista_status_display()),
        ('Lado Passageiro', checklist.get_revisao_lado_passageiro_status_display()),
    ]
    
    for item, status in items:
        ws.append([item, status, checklist.observacoes_gerais if checklist.observacoes_gerais else 'N/A'])
    
    # Adiciona assinatura
    ws.append([])
    ws.append(['Assinatura'])
    ws.merge_cells('A13:D13')
    ws.append(['Responsável pela vistoria: _________________________________________'])
    
    # Ajusta o tamanho das colunas
    for column in ['A', 'B', 'C', 'D']:
        ws.column_dimensions[column].width = 30
    
    # Salva a planilha em um buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    # Cria a resposta
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=checklist_{checklist.id}_{checklist.tipo}.xlsx'
    
    return response

def relatorio_carros(request, format):
    carros = Carro.objects.filter(ativo=True)
    
    if format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="relatorio_carros.xlsx"'
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Carros"
        
        columns = ['Placa', 'Modelo', 'Marca', 'Cor', 'Ano', 'Renavan', 'Disponível']
        ws.append(columns)
        
        for carro in carros:
            ws.append([
                carro.placa,
                carro.modelo,
                carro.marca,
                carro.cor,
                carro.ano,
                carro.renavan,
                'Sim' if carro.disponivel else 'Não'
            ])
        
        wb.save(response)
        return response
    
    elif format == 'word':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = 'attachment; filename="relatorio_carros.docx"'
        
        document = Document()
        document.add_heading('Relatório de Carros', 0)
        
        table = document.add_table(rows=1, cols=7)
        table.style = 'Table Grid'
        
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Placa'
        hdr_cells[1].text = 'Modelo'
        hdr_cells[2].text = 'Marca'
        hdr_cells[3].text = 'Cor'
        hdr_cells[4].text = 'Ano'
        hdr_cells[5].text = 'Renavan'
        hdr_cells[6].text = 'Disponível'
        
        for carro in carros:
            row_cells = table.add_row().cells
            row_cells[0].text = carro.placa
            row_cells[1].text = carro.modelo
            row_cells[2].text = carro.marca
            row_cells[3].text = carro.cor
            row_cells[4].text = str(carro.ano)
            row_cells[5].text = carro.renavan
            row_cells[6].text = 'Sim' if carro.disponivel else 'Não'
        
        document.save(response)
        return response
    
    return HttpResponse('Formato não suportado', status=400)

def carros_disponiveis(request):
    carros = Carro.objects.filter(disponivel=True, ativo=True)
    data = [{'id': carro.id, 'placa': carro.placa, 'modelo': carro.modelo} for carro in carros]
    return JsonResponse(data, safe=False)

def proxima_manutencao(request):
    hoje = datetime.now().date()
    carros = Carro.objects.filter(
        data_proxima_manutencao__lte=hoje + timedelta(days=7),
        ativo=True
    ).order_by('data_proxima_manutencao')
    
    data = [{
        'id': carro.id,
        'placa': carro.placa,
        'modelo': carro.modelo,
        'data_proxima_manutencao': carro.data_proxima_manutencao.strftime('%d/%m/%Y'),
        'dias_restantes': (carro.data_proxima_manutencao - hoje).days
    } for carro in carros]
    
    return JsonResponse(data, safe=False)

class AgendamentoUpdateView(UpdateView):
    model = Agendamento
    fields = "__all__"  # seus campos aqui
    template_name = 'automovel/agendamento_form.html'
    success_url = '/automovel/agendamentos/'  # ou use reverse_lazy

