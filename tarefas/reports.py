from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import Tarefas

def gerar_relatorio_tarefas(queryset):
    template_path = 'reports/relatorio_tarefas.html'
    context = {'tarefas': queryset}
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'filename="relatorio_tarefas.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF')
    return response