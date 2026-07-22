
# relatorio_fotografico/services/pdf_generator.py
from django.template.loader import render_to_string
from weasyprint import HTML


def _montar_fotos_urls(relatorio):
    """Dict {foto.id: url} — imagem já padronizada desde o upload."""
    return {
        foto.id: (foto.imagem.url if foto.imagem else '')
        for foto in relatorio.fotos.all()
    }


def gerar_pdf_relatorio(relatorio, request=None):
    """
    Gera o relatório em PDF via WeasyPrint, usando diretamente as
    imagens já sanitizadas/padronizadas de cada FotoRelatorio.
    """
    fotos_urls = _montar_fotos_urls(relatorio)

    html_string = render_to_string(
        'relatorio_fotografico/relatorio_pdf.html',
        {
            'relatorio': relatorio,
            'paginas': relatorio.paginas,
            'total_folhas': relatorio.total_folhas,
            'fotos_urls': fotos_urls,
        },
        request=request,
    )
    base_url = request.build_absolute_uri('/') if request else None
    return HTML(string=html_string, base_url=base_url).write_pdf()



