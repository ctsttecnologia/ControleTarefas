from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, timedelta
from openpyxl import Workbook
from docx import Document

from .models import Carro, Agendamento, Checklist, Foto
from .forms import CarroForm, AgendamentoForm, ChecklistForm, FotoForm




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

class ChecklistCreateView(LoginRequiredMixin, CreateView):
    model = Checklist
    form_class = ChecklistForm
    template_name = 'automovel/checklist_form.html'
    success_url = reverse_lazy('lista_checklists')

    def get(self, request, *args, **kwargs):
        form = ChecklistForm()
        return render(request, 'automovel:checklist_form.html', {'form': form})
    
    def get_success_url(self):
        return reverse_lazy('automovel:agendamento_detail', kwargs={'pk': self.object.agendamento.id})
    
    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, 'Checklist criado com sucesso!')
        return super().form_valid(form)

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