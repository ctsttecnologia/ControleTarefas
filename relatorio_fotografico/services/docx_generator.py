
# relatorio_fotografico/services/docx_generator.py
import io
import os

from django.conf import settings

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

from ..models import FOTOS_POR_PAGINA


def _resolver_logo_path():
    """Resolve o caminho físico de static/images/logocetest.png,
    funcionando tanto em dev (STATICFILES_DIRS) quanto após collectstatic (STATIC_ROOT)."""
    candidatos = []

    if getattr(settings, 'STATIC_ROOT', None):
        candidatos.append(os.path.join(settings.STATIC_ROOT, 'images', 'logocetest.png'))

    for static_dir in getattr(settings, 'STATICFILES_DIRS', []):
        candidatos.append(os.path.join(static_dir, 'images', 'logocetest.png'))

    for caminho in candidatos:
        if os.path.exists(caminho):
            return caminho
    return None


def _set_cell_border(cell, color="000000", sz=8):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = tc_pr.makeelement(qn('w:tcBorders'), {})
    for edge in ('top', 'left', 'bottom', 'right'):
        el = tc_borders.makeelement(qn(f'w:{edge}'), {
            qn('w:val'): 'single',
            qn('w:sz'): str(sz),
            qn('w:color'): color,
        })
        tc_borders.append(el)
    tc_pr.append(tc_borders)


def gerar_docx_relatorio(relatorio):
    doc = Document()

    section = doc.sections[0]
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(1.2)
    section.bottom_margin = Cm(1.2)

    # --- Cabeçalho com logo + título ---
    top_table = doc.add_table(rows=1, cols=3)
    top_table.autofit = False

    largura_util = section.page_width - section.left_margin - section.right_margin
    largura_logo = Cm(3)
    largura_vazio = Cm(3)
    largura_titulo = largura_util - largura_logo - largura_vazio

    top_table.columns[0].width = largura_logo
    top_table.columns[1].width = largura_titulo
    top_table.columns[2].width = largura_vazio

    cel_logo, cel_titulo, cel_vazio = top_table.rows[0].cells
    cel_logo.width = largura_logo
    cel_titulo.width = largura_titulo
    cel_vazio.width = largura_vazio

    logo_path = _resolver_logo_path()
    if logo_path:
        run_logo = cel_logo.paragraphs[0].add_run()
        run_logo.add_picture(logo_path, width=Cm(2.5))

    p_titulo = cel_titulo.paragraphs[0]
    p_titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_titulo = p_titulo.add_run('RELATÓRIO FOTOGRÁFICO')
    run_titulo.bold = True
    run_titulo.font.size = Pt(16)


    # --- Cabeçalho (tabela 3x2, agora com Responsável) ---
    header = doc.add_table(rows=3, cols=2)
    header.style = 'Table Grid'
    header.alignment = WD_TABLE_ALIGNMENT.CENTER

    header.cell(0, 0).text = f"Obra/Contrato: {relatorio.obra_codigo}"
    header.cell(0, 1).text = f"Data: {relatorio.data:%d/%m/%Y}"
    header.cell(1, 0).text = f"Assunto: {relatorio.titulo}"
    header.cell(1, 1).text = f"Folha: 01 de {relatorio.total_folhas:02d}"

    responsavel_nome = (
        relatorio.responsavel.get_full_name()
        or relatorio.responsavel.username
    )
    header.cell(2, 0).merge(header.cell(2, 1))
    header.cell(2, 0).text = f"Responsável: {responsavel_nome}"

    doc.add_paragraph()

    paginas = relatorio.paginas
    total_folhas = relatorio.total_folhas

    for pagina_idx, fotos_pagina in enumerate(paginas, start=1):
        if pagina_idx > 1:
            doc.add_page_break()
            p = doc.add_paragraph()
            run = p.add_run(
                f"{relatorio.obra_codigo} — {relatorio.titulo} "
                f"— Folha {pagina_idx:02d} de {total_folhas:02d}"
            )
            run.bold = True
            run.font.size = Pt(10)

        linhas = 3
        colunas = 2
        table = doc.add_table(rows=linhas, cols=colunas)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for idx in range(linhas * colunas):
            row = idx // colunas
            col = idx % colunas
            cell = table.cell(row, col)

            if idx < len(fotos_pagina):
                foto = fotos_pagina[idx]
                paragraph = cell.paragraphs[0]
                run = paragraph.add_run()
                try:
                    run.add_picture(foto.imagem.path, width=Cm(7.5))
                except Exception:
                    paragraph.add_run('[imagem indisponível]')
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

                legenda_p = cell.add_paragraph()
                numero_foto = idx + 1 + (pagina_idx - 1) * FOTOS_POR_PAGINA
                legenda_run = legenda_p.add_run(
                    f"Foto {numero_foto:02d}: {foto.legenda}"
                )
                legenda_run.font.size = Pt(9)
                legenda_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            else:
                cell.text = ''

    # --- Rodapé fixo em todas as páginas ---
    for sec in doc.sections:
        footer_p = sec.footer.paragraphs[0]
        footer_p.text = ''
        footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_footer = footer_p.add_run('Relatório Fotográfico — CETEST')
        run_footer.font.size = Pt(9)
        run_footer.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
