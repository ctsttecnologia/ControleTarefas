
# relatorio_fotografico/services/pdf_generator.py
from pathlib import Path

from django.template.loader import render_to_string
from weasyprint import HTML


def _montar_fotos_urls(relatorio, imagens_map):
    """
    Monta um dict {foto.id: caminho_para_template} a ser usado no HTML.

    - Se houver caminho temporário no imagens_map, converte para uma
      URI `file://` válida usando pathlib.Path.as_uri() — isso evita
      problemas de path malformado (espaços, caracteres especiais,
      barras invertidas no Windows) que fazem o WeasyPrint falhar
      silenciosamente ao carregar a imagem.
    - Caso contrário, cai no `foto.imagem.url` original (fallback).
    """
    urls = {}
    for foto in relatorio.fotos.all():
        if imagens_map:
            caminho_temp = imagens_map.get(foto.id)
            if caminho_temp:
                caminho = Path(caminho_temp)
                if caminho.exists():
                    urls[foto.id] = caminho.resolve().as_uri()
                    continue
        urls[foto.id] = foto.imagem.url if foto.imagem else ''
    return urls


def gerar_pdf_relatorio(relatorio, request=None, imagens_map=None):
    """
    Gera o relatório em PDF via WeasyPrint.

    Args:
        relatorio: instância de RelatorioFotografico.
        request: request atual (usado para resolver base_url).
        imagens_map: dict opcional {foto.id: caminho_temp_padronizado}
            gerado por `preparar_imagens_temporarias` na view.
    """
    fotos_urls = _montar_fotos_urls(relatorio, imagens_map)

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


