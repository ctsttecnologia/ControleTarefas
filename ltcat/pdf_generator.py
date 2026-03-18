
# ltcat/pdf_generator.py

"""
Motor de geração PDF do LTCAT usando ReportLab.
Layout fiel ao modelo Word oficial com:
- Capa com fundo degradê verde
- Cabeçalho com logo à direita
- Cada seção inicia em nova página
- Suporte a múltiplos locais de prestação (M2M)
"""

import os
from io import BytesIO
from datetime import date

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, Image,
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.colors import linearlyInterpolatedColor


# =============================================================================
# CONSTANTES DE LAYOUT
# =============================================================================

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_LEFT = 25 * mm
MARGIN_RIGHT = 20 * mm
MARGIN_TOP = 25 * mm
MARGIN_BOTTOM = 25 * mm
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT

# Cores
AZUL_ESCURO = colors.HexColor('#1a3a5c')
AZUL_MEDIO = colors.HexColor('#2c5f8a')
AZUL_CLARO = colors.HexColor('#d6e9f8')
CINZA_CLARO = colors.HexColor('#f5f5f5')
CINZA_MEDIO = colors.HexColor('#cccccc')
CINZA_ESCURO = colors.HexColor('#666666')

# Cores degradê da capa (verde/teal)
VERDE_ESCURO = colors.HexColor('#2a7b6f')
VERDE_CLARO = colors.HexColor('#7ec8b8')
BRANCO = colors.white

# Caminho da logo
LOGO_PATH = os.path.join(settings.BASE_DIR, 'static', 'images', 'logocetest.png')


# =============================================================================
# ESTILOS
# =============================================================================

def get_styles():
    """Retorna dicionário de estilos customizados."""
    base = getSampleStyleSheet()
    s = {}

    # Capa
    s['capa_titulo'] = ParagraphStyle(
        'capa_titulo', parent=base['Title'],
        fontSize=22, leading=28, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica-Bold',
        spaceAfter=6 * mm,
    )
    s['capa_subtitulo'] = ParagraphStyle(
        'capa_subtitulo', parent=base['Normal'],
        fontSize=13, leading=17, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica',
        spaceAfter=4 * mm,
    )
    s['capa_label'] = ParagraphStyle(
        'capa_label', parent=base['Normal'],
        fontSize=10, leading=13, alignment=TA_CENTER,
        textColor=CINZA_ESCURO, fontName='Helvetica-Bold',
        spaceAfter=1 * mm,
    )
    s['capa_valor'] = ParagraphStyle(
        'capa_valor', parent=base['Normal'],
        fontSize=12, leading=16, alignment=TA_CENTER,
        textColor=colors.black, fontName='Helvetica-Bold',
        spaceAfter=3 * mm,
    )
    s['capa_label_branco'] = ParagraphStyle(
        'capa_label_branco', parent=base['Normal'],
        fontSize=10, leading=13, alignment=TA_CENTER,
        textColor=colors.HexColor('#e0f0ed'), fontName='Helvetica-Bold',
        spaceAfter=1 * mm,
    )
    s['capa_valor_branco'] = ParagraphStyle(
        'capa_valor_branco', parent=base['Normal'],
        fontSize=14, leading=18, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica-Bold',
        spaceAfter=3 * mm,
    )

    # Títulos de seção
    s['secao_titulo'] = ParagraphStyle(
        'secao_titulo', parent=base['Heading1'],
        fontSize=13, leading=17, textColor=AZUL_ESCURO,
        fontName='Helvetica-Bold',
        spaceBefore=8 * mm, spaceAfter=4 * mm,
    )
    s['secao_subtitulo'] = ParagraphStyle(
        'secao_subtitulo', parent=base['Heading2'],
        fontSize=11, leading=15, textColor=AZUL_ESCURO,
        fontName='Helvetica-Bold',
        spaceBefore=5 * mm, spaceAfter=3 * mm,
    )
    s['subsecao_titulo'] = ParagraphStyle(
        'subsecao_titulo', parent=base['Heading3'],
        fontSize=10, leading=13, textColor=AZUL_MEDIO,
        fontName='Helvetica-Bold',
        spaceBefore=4 * mm, spaceAfter=2 * mm,
    )

    # Corpo de texto
    s['corpo'] = ParagraphStyle(
        'corpo', parent=base['Normal'],
        fontSize=10, leading=14, alignment=TA_JUSTIFY,
        fontName='Helvetica', spaceAfter=2 * mm,
    )
    s['corpo_bold'] = ParagraphStyle(
        'corpo_bold', parent=s['corpo'],
        fontName='Helvetica-Bold',
    )
    s['corpo_small'] = ParagraphStyle(
        'corpo_small', parent=s['corpo'],
        fontSize=8, leading=11,
    )
    s['corpo_center'] = ParagraphStyle(
        'corpo_center', parent=s['corpo'],
        alignment=TA_CENTER,
    )

    # Tabela
    s['th'] = ParagraphStyle(
        'th', parent=base['Normal'],
        fontSize=8, leading=10, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica-Bold',
    )
    s['td'] = ParagraphStyle(
        'td', parent=base['Normal'],
        fontSize=8, leading=10, alignment=TA_LEFT,
        fontName='Helvetica',
    )
    s['td_center'] = ParagraphStyle(
        'td_center', parent=s['td'], alignment=TA_CENTER,
    )
    s['td_bold'] = ParagraphStyle(
        'td_bold', parent=s['td'],
        fontName='Helvetica-Bold',
    )

    # Rodapé
    s['rodape'] = ParagraphStyle(
        'rodape', parent=base['Normal'],
        fontSize=7, leading=9, alignment=TA_CENTER,
        textColor=colors.grey,
    )

    return s


# =============================================================================
# CLASSE GERADORA
# =============================================================================

class LTCATPDFGenerator:
    """Classe base para geração do PDF do LTCAT."""

    def __init__(self, ltcat_documento):
        self.doc = ltcat_documento
        self.empresa = ltcat_documento.empresa
        self.local = ltcat_documento.local_prestacao_principal
        self.styles = get_styles()
        self.elements = []
        self.buffer = BytesIO()

        # Empresa LTCAT contratada (CETEST)
        # Prioridade:
        #   1. FK direta empresa_contratada no documento
        #   2. Busca EmpresaLTCAT ativa na mesma filial (fallback)
        self._empresa_ltcat = None
        try:
            from ltcat.models import EmpresaLTCAT

            # 1. FK direta do documento
            contratada = getattr(ltcat_documento, 'empresa_contratada', None)
            if contratada and contratada.ativo:
                self._empresa_ltcat = contratada
            else:
                # 2. Fallback: qualquer EmpresaLTCAT ativa da filial
                #    que NÃO seja a contratante (evita pegar o próprio cliente)
                self._empresa_ltcat = EmpresaLTCAT.objects.filter(
                    filial=ltcat_documento.filial,
                    ativo=True,
                ).exclude(
                    cliente=self.empresa  # exclui a contratante
                ).first()
        except Exception:
            pass

    @property
    def empresa_ltcat(self):
        return self._empresa_ltcat

    # ─── Dados ──────────────────────────────────────────────────

    def val(self, valor, fallback='N/I'):
        return valor if valor else fallback

    def get_razao_social(self):
        return self.val(self.empresa.razao_social if self.empresa else None)

    def get_cnpj(self):
        if self.empresa_ltcat and self.empresa_ltcat.cnpj:
            return self.empresa_ltcat.cnpj
        return self.val(getattr(self.empresa, 'cnpj', None))

    def get_cnae(self):
        if self.empresa_ltcat:
            desc = self.empresa_ltcat.descricao_cnae or ''
            cnae = self.empresa_ltcat.cnae or ''
            if cnae and desc:
                return f"{cnae} - {desc}"
            return cnae or desc or 'N/I'
        return 'N/I'

    def get_grau_risco(self):
        if self.empresa_ltcat:
            return self.val(
                self.empresa_ltcat.grau_risco_texto or self.empresa_ltcat.grau_risco
            )
        return 'N/I'

    def get_atividade(self):
        if self.empresa_ltcat:
            return self.val(self.empresa_ltcat.atividade_principal)
        return 'N/I'

    def get_num_empregados(self):
        if self.empresa_ltcat:
            return self.val(
                self.empresa_ltcat.numero_empregados_texto
                or str(self.empresa_ltcat.numero_empregados or '')
            )
        return 'N/I'

    def get_jornada(self):
        if self.empresa_ltcat:
            return self.val(self.empresa_ltcat.jornada_trabalho)
        return '44 horas semanais'

    def get_endereco_empresa(self):
        if self.empresa_ltcat:
            return self.val(self.empresa_ltcat.endereco_completo, 'Endereço não cadastrado')
        return 'Endereço não cadastrado'

    def get_empresa_campo(self, campo):
        if self.empresa_ltcat:
            return self.val(getattr(self.empresa_ltcat, campo, None))
        return 'N/I'

    def get_local_nome(self):
        return self.val(self.local.razao_social if self.local else None)

    def get_local_cnpj(self):
        return self.val(self.local.cnpj if self.local else None)

    def get_local_endereco(self):
        return self.val(self.local.endereco_completo if self.local else None)

    def get_local_campo(self, campo):
        if self.local:
            return self.val(getattr(self.local, campo, None))
        return 'N/I'

    # ─── Helpers de construção ──────────────────────────────────

    def sp(self, h=5):
        self.elements.append(Spacer(1, h * mm))

    def p(self, texto, estilo='corpo'):
        if texto:
            texto_html = texto.replace('\n', '<br/>')
            self.elements.append(Paragraph(texto_html, self.styles[estilo]))

    def titulo_secao(self, numero, titulo):
        """Título de seção — SEMPRE inicia em nova página."""
        self.elements.append(PageBreak())
        txt = f"{numero}. {titulo}" if numero else titulo
        self.elements.append(Paragraph(txt.upper(), self.styles['secao_titulo']))
        self.elements.append(HRFlowable(
            width="100%", thickness=1, color=AZUL_ESCURO, spaceAfter=3 * mm,
        ))

    def subtitulo(self, texto):
        self.elements.append(Paragraph(texto, self.styles['secao_subtitulo']))

    def campo_valor(self, campo, valor):
        self.p(f"<b>{campo}:</b> {self.val(valor)}")

    def hr(self):
        self.elements.append(HRFlowable(
            width="100%", thickness=0.5, color=CINZA_MEDIO,
            spaceBefore=2 * mm, spaceAfter=2 * mm,
        ))

    def pb(self):
        self.elements.append(PageBreak())

    # ─── Helpers de Seção (usados por _render_pagina_identificacao) ──

    def _add_section_title(self, texto):
        """Título de seção SEM quebra de página (para uso inline)."""
        self.elements.append(Spacer(1, 6 * mm))
        self.elements.append(Paragraph(texto.upper(), self.styles['secao_subtitulo']))
        self.elements.append(HRFlowable(
            width="100%", thickness=0.8, color=AZUL_ESCURO, spaceAfter=3 * mm,
        ))

    def _add_subsection_title(self, texto):
        """Subtítulo menor para sub-itens (ex: 3.1, 3.2, etc.)."""
        self.elements.append(Spacer(1, 3 * mm))
        self.elements.append(Paragraph(texto, self.styles['subsecao_titulo']))
        self.elements.append(HRFlowable(
            width="100%", thickness=0.4, color=AZUL_MEDIO, spaceAfter=2 * mm,
        ))

    def _render_key_value_table(self, campos_valores):
        """
        Renderiza tabela chave-valor estilizada.
        Recebe lista de tuplas: [('Campo:', 'Valor'), ...]
        """
        s = self.styles
        data = []
        for campo, valor in campos_valores:
            data.append([
                Paragraph(f"<b>{campo}</b>", s['td_bold']),
                Paragraph(str(valor or '—'), s['td']),
            ])

        col1 = 50 * mm
        col2 = CONTENT_WIDTH - col1
        t = Table(data, colWidths=[col1, col2])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, CINZA_MEDIO),
            ('BACKGROUND', (0, 0), (0, -1), AZUL_CLARO),
        ]))
        self.elements.append(t)
        self.elements.append(Spacer(1, 3 * mm))

    # ─── Página de Identificação (Empresas + Locais M2M) ───────

    def render_pagina_identificacao(self):
        """
        Página de Identificação — Empresas e Locais de Prestação.
        Suporta múltiplos locais via M2M (DocumentoLocalPrestacao).
        """
        self.elements.append(PageBreak())
        self.elements.append(Paragraph(
            "IDENTIFICAÇÃO", self.styles['secao_titulo']
        ))
        self.elements.append(HRFlowable(
            width="100%", thickness=1, color=AZUL_ESCURO, spaceAfter=4 * mm,
        ))

        doc = self.doc

        # ── 1. EMPRESA CONTRATADA (CETEST) ──
        contratada = doc.empresa_contratada
        if contratada:
            self._add_section_title('1. IDENTIFICAÇÃO DA EMPRESA CONTRATADA')
            dados_contratada = [
                ('Razão Social:', contratada.razao_social),
                ('CNPJ:', contratada.cnpj or '—'),
                ('CNAE:', f"{contratada.cnae} – {contratada.descricao_cnae}"
                 if contratada.cnae else '—'),
                ('Grau de Risco:', contratada.grau_risco_texto
                 or contratada.grau_risco or '—'),
                ('Atividade Principal:', contratada.atividade_principal or '—'),
                ('Nº de Empregados:', contratada.numero_empregados_texto
                 or str(contratada.numero_empregados or '—')),
                ('Jornada de Trabalho:', contratada.jornada_trabalho or '—'),
                ('Endereço:', contratada.endereco_completo),
                ('Telefone:', contratada.telefone or '—'),
                ('E-mail:', contratada.email or '—'),
            ]
            self._render_key_value_table(dados_contratada)

        # ── 2. EMPRESA CONTRATANTE (CLIENTE) ──
        self._add_section_title('2. IDENTIFICAÇÃO DA EMPRESA CONTRATANTE')
        cliente = doc.empresa
        endereco_cliente = ''
        if cliente:
            logradouro = getattr(cliente, 'logradouro', None)
            if logradouro:
                partes = filter(None, [
                    logradouro.endereco,
                    f"nº {logradouro.numero}" if logradouro.numero else None,
                    logradouro.complemento,
                    logradouro.bairro,
                    f"{logradouro.cidade}/{logradouro.estado}"
                    if logradouro.cidade else None,
                    f"CEP: {logradouro.cep}" if logradouro.cep else None,
                ])
                endereco_cliente = ', '.join(partes)

        dados_contratante = [
            ('Razão Social:', cliente.razao_social if cliente else '—'),
            ('CNPJ:', getattr(cliente, 'cnpj', '') or '—'),
            ('Contrato:', getattr(cliente, 'contrato', '') or '—'),
            ('Endereço:', endereco_cliente or '—'),
        ]
        self._render_key_value_table(dados_contratante)

        # ── 3. LOCAIS DE PRESTAÇÃO DE SERVIÇO (MÚLTIPLOS via M2M) ──
        locais = doc.documento_locais.select_related(
            'local_prestacao', 'local_prestacao__logradouro'
        ).order_by('-principal', 'ordem')

        if locais.exists():
            self._add_section_title('3. LOCAIS DE PRESTAÇÃO DE SERVIÇO')

            for i, vinculo in enumerate(locais, 1):
                local = vinculo.local_prestacao
                flag = ' ★ (Principal)' if vinculo.principal else ''

                self._add_subsection_title(f'3.{i}. {local.nome_local}{flag}')

                dados_local = [
                    ('Razão Social:', local.razao_social or '—'),
                    ('CNPJ:', local.cnpj or '—'),
                    ('Endereço:', local.endereco_completo),
                ]
                if local.descricao:
                    dados_local.append(('Descrição:', local.descricao))
                if vinculo.observacoes:
                    dados_local.append(('Observações:', vinculo.observacoes))

                self._render_key_value_table(dados_local)

    # ─── Tabelas ────────────────────────────────────────────────

    def tabela(self, headers, dados, col_widths=None, zebra=True):
        s = self.styles
        header_row = [Paragraph(h, s['th']) for h in headers]
        table_data = [header_row]

        for row in dados:
            table_row = []
            for cell in row:
                if isinstance(cell, Paragraph):
                    table_row.append(cell)
                else:
                    table_row.append(Paragraph(str(cell or ''), s['td']))
            table_data.append(table_row)

        if col_widths:
            widths = [w * mm for w in col_widths]
        else:
            widths = [CONTENT_WIDTH / len(headers)] * len(headers)

        t = Table(table_data, colWidths=widths, repeatRows=1)
        cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), AZUL_ESCURO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, CINZA_MEDIO),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, AZUL_ESCURO),
        ]
        if zebra and len(table_data) > 1:
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    cmds.append(('BACKGROUND', (0, i), (-1, i), CINZA_CLARO))
        t.setStyle(TableStyle(cmds))
        self.elements.append(t)

    def tabela_campos(self, campos_valores):
        s = self.styles
        data = []
        for campo, valor in campos_valores:
            data.append([
                Paragraph(f"<b>{campo}:</b>", s['td_bold']),
                Paragraph(str(valor or 'N/I'), s['td']),
            ])
        col1 = 50 * mm
        col2 = CONTENT_WIDTH - col1
        t = Table(data, colWidths=[col1, col2])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, CINZA_MEDIO),
            ('BACKGROUND', (0, 0), (0, -1), AZUL_CLARO),
        ]))
        self.elements.append(t)

    def tabela_capa(self, label, valor):
        s = self.styles
        data = [
            [Paragraph(label, s['capa_label_branco'])],
            [Paragraph(f"<b>{valor}</b>", s['capa_valor_branco'])],
        ]
        t = Table(data, colWidths=[CONTENT_WIDTH])
        t.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.white),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.15)),
        ]))
        self.elements.append(t)

    # ─── Cabeçalho com Logo / Rodapé ────────────────────────────

    def _header_footer(self, canvas, doc):
        """Cabeçalho e rodapé para páginas internas (não capa)."""
        canvas.saveState()
        w, h = A4

        # ── CABEÇALHO ──
        header_y = h - 18 * mm

        # Texto à esquerda
        canvas.setFont('Helvetica-Bold', 8)
        canvas.setFillColor(AZUL_ESCURO)
        canvas.drawString(
            MARGIN_LEFT, header_y + 2 * mm,
            "LTCAT - LAUDO TÉCNICO DAS CONDIÇÕES AMBIENTAIS DO TRABALHO"
        )

        # Logo à direita
        logo_path = LOGO_PATH
        if os.path.exists(logo_path):
            try:
                logo_w = 30 * mm
                logo_h = 12 * mm
                logo_x = w - MARGIN_RIGHT - logo_w
                logo_y = header_y - 2 * mm
                canvas.drawImage(
                    logo_path, logo_x, logo_y, logo_w, logo_h,
                    preserveAspectRatio=True, mask='auto',
                )
            except Exception:
                canvas.setFont('Helvetica-Bold', 10)
                canvas.setFillColor(AZUL_MEDIO)
                canvas.drawRightString(w - MARGIN_RIGHT, header_y + 2 * mm, "CETEST")

        # Linha do cabeçalho
        canvas.setStrokeColor(CINZA_MEDIO)
        canvas.setLineWidth(1)
        canvas.line(MARGIN_LEFT, header_y - 4 * mm, w - MARGIN_RIGHT, header_y - 4 * mm)

        # ── RODAPÉ ──
        rodape_y = MARGIN_BOTTOM - 8 * mm

        canvas.setStrokeColor(CINZA_MEDIO)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_LEFT, rodape_y + 4 * mm, w - MARGIN_RIGHT, rodape_y + 4 * mm)

        canvas.setFont('Helvetica', 6)
        canvas.setFillColor(colors.grey)

        # Esquerda: nome do documento
        razao = self.get_razao_social()[:50]
        canvas.drawString(MARGIN_LEFT, rodape_y,
                          f"LTCAT — {razao}")

        # Centro: revisão e data
        data_elab = (self.doc.data_elaboracao.strftime('%d/%m/%Y')
                     if self.doc.data_elaboracao else 'N/I')
        canvas.drawCentredString(w / 2, rodape_y,
                                 f"Rev. {self.doc.versao_atual:02d} — {data_elab}")

        # Direita: página
        canvas.drawRightString(w - MARGIN_RIGHT, rodape_y,
                               f"Página {doc.page}")

        canvas.restoreState()

    def _first_page(self, canvas, doc):
        """Página da capa — fundo degradê verde."""
        canvas.saveState()
        w, h = A4

        # ── DEGRADÊ VERDE ──
        num_strips = 200
        strip_h = h / num_strips

        for i in range(num_strips):
            ratio = i / num_strips
            r = VERDE_ESCURO.red + (VERDE_CLARO.red - VERDE_ESCURO.red) * ratio
            g = VERDE_ESCURO.green + (VERDE_CLARO.green - VERDE_ESCURO.green) * ratio
            b = VERDE_ESCURO.blue + (VERDE_CLARO.blue - VERDE_ESCURO.blue) * ratio

            canvas.setFillColorRGB(r, g, b)
            y = h - (i + 1) * strip_h
            canvas.rect(0, y, w, strip_h + 0.5, stroke=0, fill=1)

        # ── LOGO GRANDE NA CAPA ──
        if os.path.exists(LOGO_PATH):
            try:
                logo_w = 60 * mm
                logo_h = 25 * mm
                logo_x = (w - logo_w) / 2
                logo_y = h - 60 * mm
                canvas.drawImage(
                    LOGO_PATH, logo_x, logo_y, logo_w, logo_h,
                    preserveAspectRatio=True, mask='auto',
                )
            except Exception:
                pass

        # ── CONFIDENCIAL NO RODAPÉ DA CAPA ──
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.Color(1, 1, 1, alpha=0.6))
        canvas.drawCentredString(w / 2, 15 * mm,
                                 "Documento confidencial — Uso restrito da empresa")

        canvas.restoreState()

    # ─── Build ──────────────────────────────────────────────────

    def build(self):
        doc = SimpleDocTemplate(
            self.buffer, pagesize=A4,
            leftMargin=MARGIN_LEFT, rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
            title=f"LTCAT - {self.doc.codigo_documento}",
            author="Sistema SST",
        )
        doc.build(
            self.elements,
            onFirstPage=self._first_page,
            onLaterPages=self._header_footer,
        )
        self.buffer.seek(0)
        return self.buffer.getvalue()

