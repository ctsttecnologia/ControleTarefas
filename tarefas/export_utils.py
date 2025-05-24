from django.http import HttpResponse
from django.template.loader import render_to_string
import csv
from io import StringIO
from weasyprint import HTML

def export_pdf(queryset):
    html_string = render_to_string('tarefas/relatorio_pdf.html', {'tarefas': queryset})
    html = HTML(string=html_string)
    pdf = html.write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_tarefas.pdf"'
    return response

def export_csv(queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_tarefas.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Título', 'Status', 'Data Criação', 'Prazo', 'Responsável'])
    
    for tarefa in queryset:
        writer.writerow([
            tarefa.titulo,
            tarefa.get_status_display(),
            tarefa.data_criacao.strftime('%d/%m/%Y'),
            tarefa.prazo.strftime('%d/%m/%Y') if tarefa.prazo else '-',
            tarefa.usuario.username
        ])
    
    return response

