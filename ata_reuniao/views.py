# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib import messages
from django.template.loader import get_template
from xhtml2pdf import pisa
import csv
from datetime import datetime

from .models import AtaReuniao
from .forms import AtaReuniaoForm

class AtaReuniaoListView(ListView):
    model = AtaReuniao
    template_name = 'ata_reuniao/ata_reuniao_list.html'
    context_object_name = 'atas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        natureza = self.request.GET.get('natureza')
        
        if status:
            queryset = queryset.filter(status=status)
        if natureza:
            queryset = queryset.filter(natureza=natureza)
            
        return queryset.order_by('-entrada')

class AtaReuniaoCreateView(CreateView):
    model = AtaReuniao
    form_class = AtaReuniaoForm
    template_name = 'ata_reuniao/ata_form.html'
    success_url = reverse_lazy('ata_reuniao_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Ata de reunião criada com sucesso!')
        return super().form_valid(form)

class AtaReuniaoUpdateView(UpdateView):
    model = AtaReuniao
    form_class = AtaReuniaoForm
    template_name = 'ata_reuniao/ata_form.html'
    success_url = reverse_lazy('ata_reuniao_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Ata de reunião atualizada com sucesso!')
        return super().form_valid(form)

class AtaReuniaoDeleteView(DeleteView):
    model = AtaReuniao
    template_name = 'ata_reuniao/ata_confirm_delete.html'
    success_url = reverse_lazy('ata_reuniao_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Ata de reunião excluída com sucesso!')
        return super().delete(request, *args, **kwargs)

def exportar_pdf(request):
    atas = AtaReuniao.objects.all().order_by('-entrada')
    
    template_path = 'ata_reuniao/ata_pdf.html'
    context = {'atas': atas}
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="atas_reuniao.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF')
    return response

def exportar_excel(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="atas_reuniao.csv"'
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'ID', 'Contrato', 'Coordenador', 'Responsável', 'Natureza', 
        'Ação', 'Entrada', 'Prazo', 'Status'
    ])
    
    atas = AtaReuniao.objects.all().order_by('-entrada')
    for ata in atas:
        writer.writerow([
            ata.id,
            ata.contrato,
            ata.coordenador,
            ata.responsavel,
            ata.get_natureza_display(),
            ata.acao,
            ata.entrada.strftime('%d/%m/%Y'),
            ata.prazo.strftime('%d/%m/%Y') if ata.prazo else '',
            ata.get_status_display(),
        ])
    
    return response


