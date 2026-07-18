
# relatorio_fotografico/services/pdf_generator.py
from django.template.loader import render_to_string
from weasyprint import HTML


def gerar_pdf_relatorio(relatorio, request=None):
    html_string = render_to_string(
        'relatorio_fotografico/relatorio_pdf.html',
        {
            'relatorio': relatorio,
            'paginas': relatorio.paginas,
            'total_folhas': relatorio.total_folhas,
        },
        request=request,
    )
    base_url = request.build_absolute_uri('/') if request else None
    return HTML(string=html_string, base_url=base_url).write_pdf()

