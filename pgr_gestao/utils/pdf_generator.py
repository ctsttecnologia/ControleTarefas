
"""
Gerador de PDF para relatório PGR conforme modelo oficial
"""
import logging
from pathlib import Path
from io import BytesIO
from datetime import date

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether, Frame, PageTemplate,
    NextPageTemplate, SimpleDocTemplate
)
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from pgr_gestao.services import inicializar_secoes_pgr, get_texto_secao, get_titulo_secao
from pypdf import PdfReader, PdfWriter
from pgr_gestao.models import AnexoPGR
import os



logger = logging.getLogger(__name__)


# =============================================================================
# FUNÇÕES DE CALLBACK (fora da classe — exigido pelo ReportLab onPage)
# =============================================================================

def _find_logo_path():
    """Busca o logo nos caminhos possíveis do projeto"""
    possiveis_logos = [
        Path(settings.MEDIA_ROOT) / 'logocetest.png',
        Path(settings.BASE_DIR) / 'static' / 'images' / 'logocetest.png',
        Path(settings.BASE_DIR) / 'midia' / 'logocetest.png',
    ]
    for caminho in possiveis_logos:
        try:
            if caminho.exists() and caminho.is_file():
                return caminho
        except Exception:
            continue
    return None


# Cache do logo (busca uma vez só)
_LOGO_PATH = _find_logo_path()


def draw_capa_background(canvas_obj, doc):
    """
    Desenha o fundo azul, linhas decorativas e logo da capa.
    Callback onPage do PageTemplate 'capa'.
    """
    canvas_obj.saveState()
    width, height = A4

    # =========================================================
    # 1. FUNDO AZUL ESCURO (gradiente simulado)
    # =========================================================
    cor_escura = colors.HexColor('#1B3A5C')
    cor_media = colors.HexColor('#2A5580')

    canvas_obj.setFillColor(cor_escura)
    canvas_obj.rect(0, 0, width, height, fill=True, stroke=False)

    # Faixa mais clara no centro
    canvas_obj.setFillColor(cor_media)
    canvas_obj.rect(0, height * 0.25, width, height * 0.45, fill=True, stroke=False)

    # =========================================================
    # 2. LINHAS DIAGONAIS DECORATIVAS
    # =========================================================
    canvas_obj.setStrokeColor(colors.HexColor('#4A7FAA'))
    canvas_obj.setLineWidth(0.8)

    linhas = [
        (width * 0.30, height * 0.95, width * 0.95, height * 0.55),
        (width * 0.28, height * 0.93, width * 0.93, height * 0.53),
        (width * 0.32, height * 0.92, width * 0.97, height * 0.52),
        (width * 0.25, height * 0.90, width * 0.90, height * 0.50),
        (width * 0.35, height * 0.91, width * 0.99, height * 0.51),
    ]
    for x1, y1, x2, y2 in linhas:
        canvas_obj.line(x1, y1, x2, y2)

    canvas_obj.setStrokeColor(colors.HexColor('#3A6F9A'))
    canvas_obj.setLineWidth(0.4)
    linhas_finas = [
        (width * 0.33, height * 0.96, width * 0.96, height * 0.56),
        (width * 0.26, height * 0.91, width * 0.91, height * 0.51),
        (width * 0.37, height * 0.93, width * 1.00, height * 0.53),
        (width * 0.22, height * 0.88, width * 0.88, height * 0.48),
    ]
    for x1, y1, x2, y2 in linhas_finas:
        canvas_obj.line(x1, y1, x2, y2)

    # =========================================================
    # 3. BARRA BRANCA DO CABEÇALHO (topo)
    # =========================================================
    barra_y = height - 2.2 * cm
    barra_altura = 1.8 * cm

    canvas_obj.setFillColor(colors.white)
    canvas_obj.rect(0, barra_y, width, barra_altura, fill=True, stroke=False)

    canvas_obj.setFillColor(colors.HexColor('#333333'))
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.drawString(
        1.5 * cm,
        barra_y + barra_altura / 2 - 2,
        "PROGRAMA DE GESTÃO DE RISCOS – PGR"
    )

    # Linha separadora abaixo do cabeçalho
    canvas_obj.setStrokeColor(colors.HexColor('#003366'))
    canvas_obj.setLineWidth(1.5)
    canvas_obj.line(1.5 * cm, barra_y, width - 1.5 * cm, barra_y)

    # =========================================================
    # 4. LOGO NO CANTO SUPERIOR DIREITO
    # =========================================================
    if _LOGO_PATH:
        try:
            logo_w = 3.5 * cm
            logo_h = 1.2 * cm
            logo_x = width - logo_w - 1.5 * cm
            logo_y = barra_y + (barra_altura - logo_h) / 2
            canvas_obj.drawImage(
                str(_LOGO_PATH),
                logo_x, logo_y,
                width=logo_w, height=logo_h,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception as e:
            logger.error(f"Erro ao desenhar logo na capa: {e}")

    canvas_obj.restoreState()


def draw_header_footer(canvas_obj, doc):
    """
    Desenha cabeçalho e rodapé nas páginas normais (não-capa).
    Callback onPage do PageTemplate 'normal'.
    """
    canvas_obj.saveState()
    width, height = A4

     # ===== CABEÇALHO =====
    # Linha superior
    canvas_obj.setStrokeColor(colors.HexColor('#003366'))
    canvas_obj.setLineWidth(1)
    canvas_obj.line(1.5 * cm, height - 1.5 * cm, width - 1.5 * cm, height - 1.5 * cm)

    # Logo no cabeçalho (direita)
    if _LOGO_PATH:
        try:
            logo_w = 2.5 * cm
            logo_h = 0.9 * cm
            canvas_obj.drawImage(
                str(_LOGO_PATH),
                width - logo_w - 1.5 * cm,  # Alinhado à direita
                height - 1.4 * cm,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception:
            pass

    # Título no cabeçalho (esquerda)
    canvas_obj.setFillColor(colors.HexColor('#003366'))
    canvas_obj.setFont('Helvetica-Bold', 8)
    canvas_obj.drawString(
        1.5 * cm,               # Alinhado à margem esquerda
        height - 1.3 * cm,
        "PROGRAMA DE GESTÃO DE RISCOS – PGR"
    )

    # ===== RODAPÉ =====
    canvas_obj.setStrokeColor(colors.HexColor('#003366'))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(1.5 * cm, 1.5 * cm, width - 1.5 * cm, 1.5 * cm)

    # Número da página
    canvas_obj.setFillColor(colors.HexColor('#666666'))
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.drawRightString(
        width - 1.5 * cm,
        1.0 * cm,
        f"Página {doc.page}"
    )

    # Texto do rodapé (esquerda)
    canvas_obj.drawString(
        1.5 * cm,
        1.0 * cm,
        "PGR – Programa de Gestão de Riscos"
    )

    canvas_obj.restoreState()


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class PGRPDFGenerator:
    """
    Classe para gerar PDF do PGR conforme modelo oficial
    """

    def __init__(self, pgr_documento):
        self.pgr = pgr_documento
        self.cliente = pgr_documento.empresa
        self.local_prestacao = pgr_documento.local_prestacao
        self.width, self.height = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.empresa_pgr = self._get_empresa_pgr()
        self.empresa_contratada = self._get_empresa_contratada()

    # =================================================================
    # INICIALIZAÇÃO
    # =================================================================

    def _get_empresa_pgr(self):
        """Busca o objeto Empresa PGR vinculado ao Cliente, se existir"""
        try:
            from pgr_gestao.models import Empresa
            return Empresa.objects.filter(
                cliente=self.cliente,
                ativo=True
            ).first()
        except Exception:
            return None

    def _get_empresa_contratada(self):
        """
        Busca a empresa CONTRATADA (prestadora de serviços).
        No modelo oficial, é ela que aparece como 'EMPRESA' na capa.
        """
        try:
            from pgr_gestao.models import Empresa
            contratada = Empresa.objects.filter(
                filial=self.pgr.filial,
                tipo_empresa__in=['contratada', 'prestadora'],
                ativo=True
            ).first()
            return contratada
        except Exception:
            return None

    def _setup_custom_styles(self):
        """Configura estilos customizados para o documento"""
        self.styles.add(ParagraphStyle(
            name='TituloCapa',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#003366'),
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='SubtituloCapa',
            parent=self.styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='TituloSecao',
            parent=self.styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#003366'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='Justificado',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=14
        ))
        self.styles.add(ParagraphStyle(
            name='TabelaTexto',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='TabelaTextoCentro',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='TabelaTitulo',
            parent=self.styles['Normal'],
            fontSize=7,
            fontName='Helvetica-Bold',
            textColor=colors.white,
            alignment=TA_CENTER,
            leading=9
        ))
        self.styles.add(ParagraphStyle(
            name='CampoLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            leading=12
        ))
        self.styles.add(ParagraphStyle(
            name='CampoValor',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=12
        ))

    # =================================================================
    # HELPERS
    # =================================================================

    def _get_dado(self, campo, fallback='N/A'):
        """
        Busca um dado primeiro na Empresa Contratada (PGR),
        depois na Empresa PGR genérica, depois no Cliente.
        """
        for fonte in [self.empresa_contratada, self.empresa_pgr, self.cliente]:
            if fonte:
                valor = getattr(fonte, campo, None)
                if valor not in (None, ''):
                    return str(valor)
        return fallback

    def _get_nome_empresa(self):
        """Retorna o nome da empresa contratada (para uso nos textos)"""
        if self.empresa_contratada:
            return self.empresa_contratada.razao_social
        return self.cliente.razao_social

    # =================================================================
    # CAPA
    # =================================================================

    def _criar_capa(self):
        """Cria a página de capa do PGR com design profissional azul"""
        story = []

        # Espaçamento inicial (abaixo da barra branca do cabeçalho)
        story.append(Spacer(1, 6 * cm))

        # ===== ESTILOS ESPECÍFICOS DA CAPA =====
        estilo_titulo_pgr = ParagraphStyle(
            'CapaTituloPGR',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=28,
            textColor=colors.white,
            leading=34,
            spaceAfter=0,
        )

        estilo_subtitulo_pgr = ParagraphStyle(
            'CapaSubtituloPGR',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.white,
            leading=20,
            spaceAfter=0,
        )

        estilo_label = ParagraphStyle(
            'CapaLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#A0C4E8'),
            leading=12,
            spaceBefore=20,
            spaceAfter=2,
        )

        estilo_valor = ParagraphStyle(
            'CapaValor',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.white,
            leading=20,
            spaceAfter=0,
        )

        estilo_valor_destaque = ParagraphStyle(
            'CapaValorDestaque',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            textColor=colors.HexColor("#FFFFFF"),
            leading=22,
            spaceAfter=0,
        )

        # ===== PGR — TÍTULO PRINCIPAL =====
        story.append(Paragraph("PGR", estilo_titulo_pgr))
        story.append(Paragraph("PROGRAMA DE GESTÃO DE RISCOS", estilo_subtitulo_pgr))
        story.append(Spacer(1, 1.5 * cm))

        # ===== EMPRESA =====
        nome_empresa = self._get_nome_empresa()
        story.append(Paragraph("EMPRESA", estilo_label))
        story.append(Paragraph(nome_empresa.upper(), estilo_valor))
        story.append(Spacer(1, 1 * cm))

        # ===== LOCAL DE TRABALHO =====
        local_nome = ''
        local_cidade = ''
        if self.local_prestacao:
            local_nome = (self.local_prestacao.razao_social or '').upper()
            cidade = getattr(self.local_prestacao, 'cidade', '') or ''
            estado = getattr(self.local_prestacao, 'estado', '') or ''
            if cidade and estado:
                local_cidade = f"{cidade.upper()} / {estado.upper()}"
        else:
            local_nome = self.cliente.razao_social.upper()

        story.append(Paragraph("LOCAL DE TRABALHO", estilo_label))
        story.append(Paragraph(local_nome, estilo_valor))

        if local_cidade:
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph(local_cidade, estilo_valor_destaque))

        story.append(Spacer(1, 1 * cm))

        # ===== REVISÃO =====
        revisao_texto = 'Primeira Versão'
        if self.pgr.data_ultima_revisao:
            meses_pt = {
                1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
                5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
                9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
            }
            mes = meses_pt.get(self.pgr.data_ultima_revisao.month, '')
            ano = self.pgr.data_ultima_revisao.year
            revisao_texto = f"{mes} /{ano}"

        story.append(Paragraph("REVISÃO", estilo_label))
        story.append(Paragraph(revisao_texto, estilo_valor_destaque))
        story.append(Spacer(1, 2 * cm))

        # ===== TABELA DE DATAS (parte inferior) =====
        estilo_data_header = ParagraphStyle(
            'DataHeader',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=colors.white,
            alignment=TA_CENTER,
        )

        estilo_data_valor = ParagraphStyle(
            'DataValor',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.HexColor('#1B3A5C'),
            alignment=TA_CENTER,
        )

        data_elaboracao = self.pgr.data_elaboracao.strftime('%d/%m/%Y')
        data_revisao = (
            self.pgr.data_ultima_revisao.strftime('%d/%m/%Y')
            if self.pgr.data_ultima_revisao else 'N/A'
        )
        data_vencimento = self.pgr.data_vencimento.strftime('%d/%m/%Y')

        data_datas = [
            [
                Paragraph('ELABORAÇÃO', estilo_data_header),
                Paragraph('DATA DA ÚLTIMA REVISÃO', estilo_data_header),
                Paragraph('DATA DO VENCIMENTO', estilo_data_header),
            ],
            [
                Paragraph(data_elaboracao, estilo_data_valor),
                Paragraph(data_revisao, estilo_data_valor),
                Paragraph(data_vencimento, estilo_data_valor),
            ],
        ]

        table_datas = Table(data_datas, colWidths=[5.3 * cm, 5.3 * cm, 5.3 * cm])
        table_datas.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('BACKGROUND', (0, 1), (-1, 1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#003366')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table_datas)

        # ===== TROCA PARA TEMPLATE NORMAL + QUEBRA DE PÁGINA =====
        story.append(NextPageTemplate('normal'))
        story.append(PageBreak())

        return story

    # =================================================================
    # CARACTERIZAÇÃO DA EMPRESA
    # =================================================================

    def _criar_caracterizacao_empresa(self):
        """
        Cria a seção de caracterização da empresa conforme modelo oficial.
        Mostra os dados da empresa CONTRATADA (quem presta o serviço).
        """
        story = []
        story.append(Paragraph("CARACTERIZAÇÃO DA EMPRESA", self.styles['TituloSecao']))

        # Razão Social
        razao_social = self._get_nome_empresa()

        # CNPJ
        cnpj = 'N/A'
        if self.empresa_contratada:
            cnpj = self.empresa_contratada.cnpj or 'N/A'
            if cnpj == 'N/A' and self.empresa_contratada.cliente:
                cnpj = getattr(self.empresa_contratada.cliente, 'cnpj', 'N/A') or 'N/A'
        elif self.empresa_pgr:
            cnpj = self.empresa_pgr.cnpj or 'N/A'

        # CNAE
        cnae_texto = 'N/A'
        for fonte in [self.empresa_contratada, self.empresa_pgr]:
            if fonte:
                cnae_val = getattr(fonte, 'cnae', '') or ''
                desc_cnae = getattr(fonte, 'descricao_cnae', '') or ''
                if cnae_val:
                    cnae_texto = f"{cnae_val} - {desc_cnae}" if desc_cnae else cnae_val
                    break

        # Grau de Risco
        grau_texto = self._get_dado('grau_risco_texto', '')
        if not grau_texto or grau_texto == 'N/A':
            grau_texto = self._get_dado('grau_risco', 'N/A')

        # Nº de Empregados
        num_emp = self._get_dado('numero_empregados_texto', '')
        if not num_emp or num_emp == 'N/A':
            num_emp = self._get_dado('numero_empregados', 'N/A')

        # Endereço completo
        endereco = self._get_dado('endereco', 'N/A')
        numero = self._get_dado('numero', '')
        complemento = self._get_dado('complemento', '')

        endereco_completo = endereco
        if numero and numero != 'N/A':
            endereco_completo = f"{endereco}, {numero}"
        if complemento and complemento != 'N/A':
            endereco_completo = f"{endereco_completo} - {complemento}"

        dados_empresa = [
            ['RAZÃO SOCIAL:', razao_social],
            ['CNPJ:', cnpj],
            ['CNAE:', cnae_texto],
            ['GRAU DE RISCO:', grau_texto],
            ['ATIVIDADE:', self._get_dado('atividade_principal', 'N/A')],
            ['Nº DE EMPREGADOS:', num_emp],
            ['JORNADA DE TRABALHO:', self._get_dado('jornada_trabalho', '44 horas semanais')],
            ['ENDEREÇO:', endereco_completo],
            ['BAIRRO:', self._get_dado('bairro', 'N/A')],
            ['CIDADE/UF:', f"{self._get_dado('cidade', 'N/A')} - {self._get_dado('estado', '')}"],
            ['CEP:', self._get_dado('cep', 'N/A')],
            ['TELEFONE:', self._get_dado('telefone', 'N/A')],
        ]

        table = Table(dados_empresa, colWidths=[4.5 * cm, 11.5 * cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5 * cm))

        # LOCAL DA PRESTAÇÃO DE SERVIÇOS
        if self.local_prestacao:
            story.append(Paragraph(
                "LOCAL DA PRESTAÇÃO DE SERVIÇOS", self.styles['TituloSecao']
            ))
            dados_local = [
                ['RAZÃO SOCIAL:', self.local_prestacao.razao_social or 'N/A'],
                ['CNPJ:', getattr(self.local_prestacao, 'cnpj', '') or 'N/A'],
                [
                    'ENDEREÇO:',
                    f"{getattr(self.local_prestacao, 'endereco', '') or ''}, "
                    f"{getattr(self.local_prestacao, 'numero', '') or ''}".strip(', ')
                ],
                ['BAIRRO:', getattr(self.local_prestacao, 'bairro', '') or 'N/A'],
                [
                    'CIDADE/UF:',
                    f"{getattr(self.local_prestacao, 'cidade', '')} - "
                    f"{getattr(self.local_prestacao, 'estado', '')}"
                ],
                ['CEP:', getattr(self.local_prestacao, 'cep', '') or 'N/A'],
            ]
            table_local = Table(dados_local, colWidths=[4.5 * cm, 11.5 * cm])
            table_local.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(table_local)
            story.append(Spacer(1, 0.5 * cm))

        # RESPONSÁVEIS PELA ELABORAÇÃO DO PGR
        responsavel_info_qs = self.pgr.responsavel_info.select_related(
            'profissional'
        ).all()

        if responsavel_info_qs.exists():
            story.append(Paragraph(
                "RESPONSÁVEIS PELA ELABORAÇÃO DO PGR", self.styles['TituloSecao']
            ))

            for resp_info in responsavel_info_qs:
                prof = resp_info.profissional
                if prof:
                    registro = ''
                    if prof.registro_classe:
                        orgao = prof.orgao_classe or ''
                        registro = f"{orgao} {prof.registro_classe}".strip()

                    dados_resp = [
                        ['NOME:', prof.nome_completo or 'N/A'],
                        ['FUNÇÃO:', prof.funcao or 'N/A'],
                        ['REGISTRO DE CLASSE:', registro or 'N/A'],
                    ]
                    table_resp = Table(dados_resp, colWidths=[5 * cm, 11 * cm])
                    table_resp.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ]))
                    story.append(table_resp)
                    story.append(Spacer(1, 0.3 * cm))

        story.append(PageBreak())
        return story

    # =================================================================
    # 1. CONTROLE DE REVISÃO
    # =================================================================

    def _criar_controle_revisao(self):
        """Cria a tabela de controle de revisão conforme modelo oficial"""
        story = []
        story.append(Paragraph("1. CONTROLE DE REVISÃO", self.styles['TituloSecao']))

        dados_revisao = [[
            Paragraph('<b>REVISÃO</b>', self.styles['TabelaTitulo']),
            Paragraph('<b>DESCRIÇÃO</b>', self.styles['TabelaTitulo']),
            Paragraph('<b>REALIZADA</b>', self.styles['TabelaTitulo'])
        ]]

        revisoes = self.pgr.revisoes.all().order_by('numero_revisao')
        if revisoes.exists():
            for revisao in revisoes:
                dados_revisao.append([
                    Paragraph(
                        f"{revisao.numero_revisao:02d}",
                        self.styles['TabelaTextoCentro']
                    ),
                    Paragraph(
                        revisao.descricao_revisao or '',
                        self.styles['TabelaTexto']
                    ),
                    Paragraph(
                        revisao.data_realizacao.strftime('%d/%m/%Y'),
                        self.styles['TabelaTextoCentro']
                    )
                ])
        else:
            dados_revisao.append([
                Paragraph("00", self.styles['TabelaTextoCentro']),
                Paragraph(
                    "Emissão inicial (Elaboração do PGR)",
                    self.styles['TabelaTexto']
                ),
                Paragraph(
                    self.pgr.data_elaboracao.strftime('%d/%m/%Y'),
                    self.styles['TabelaTextoCentro']
                )
            ])

        table_revisao = Table(
            dados_revisao, colWidths=[2.5 * cm, 10.5 * cm, 3 * cm]
        )
        table_revisao.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table_revisao)
        story.append(PageBreak())
        return story
    
    # =================================================================
    # HELPERS (adicionar dentro da classe PGRPDFGenerator)
    # =================================================================

    def _texto_para_paragrafos(self, texto, estilo=None):
        """
        Converte texto com \n e \n\n em lista de Paragraph do ReportLab.
        
        - \n\n → novo Paragraph (bloco separado)
        - \n   → <br/> dentro do mesmo Paragraph (quebra de linha visual)
        
        Isso garante que alíneas a), b), c) fiquem em linhas separadas.
        """
        if not texto:
            return []
        
        if estilo is None:
            estilo = self.styles['Justificado']
        
        story = []
        # Separa por parágrafo (dupla quebra)
        blocos = texto.split('\n\n')
        
        for bloco in blocos:
            bloco = bloco.strip()
            if not bloco:
                continue
            # Dentro de cada bloco, \n vira <br/> para o ReportLab
            bloco_html = bloco.replace('\n', '<br/>')
            story.append(Paragraph(bloco_html, estilo))
        
        return story

    # =================================================================
    # 2. DOCUMENTO BASE
    # =================================================================

    def _criar_documento_base(self):
        """Cria a seção de documento base usando textos do banco de dados"""
        nome_empresa = self._get_nome_empresa()
        story = []

        titulo = get_titulo_secao(self.pgr, 'documento_base') or '2. DOCUMENTO BASE'
        story.append(Paragraph(titulo, self.styles['TituloSecao']))
        story.append(Paragraph(
            "PGR – PROGRAMA DE GERENCIAMENTO DE RISCOS",
            self.styles['SubtituloCapa']
        ))

        texto = get_texto_secao(self.pgr, 'documento_base', nome_empresa)
        if texto:
            story.extend(self._texto_para_paragrafos(texto))

        # METAS
        texto_metas = get_texto_secao(self.pgr, 'documento_base_metas', nome_empresa)
        if texto_metas:
            titulo_metas = get_titulo_secao(self.pgr, 'documento_base_metas') or 'METAS'
            story.append(Paragraph(titulo_metas, self.styles['TituloSecao']))
            story.extend(self._texto_para_paragrafos(texto_metas))

        # OBJETIVO GERAL
        texto_objetivo = (
            self.pgr.objetivo
            or get_texto_secao(self.pgr, 'documento_base_objetivo', nome_empresa)
        )
        if texto_objetivo:
            titulo_obj = get_titulo_secao(self.pgr, 'documento_base_objetivo') or 'OBJETIVO GERAL'
            story.append(Paragraph(titulo_obj, self.styles['TituloSecao']))
            story.extend(self._texto_para_paragrafos(texto_objetivo))

        story.append(PageBreak())
        return story

    # =================================================================
    # 3. DEFINIÇÕES
    # =================================================================

    def _criar_definicoes(self):
        """Cria a seção de definições usando textos do banco de dados"""
        nome_empresa = self._get_nome_empresa()
        story = []

        titulo = get_titulo_secao(self.pgr, 'definicoes') or '3. DEFINIÇÕES'
        story.append(Paragraph(titulo, self.styles['TituloSecao']))

        texto = get_texto_secao(self.pgr, 'definicoes', nome_empresa)
        if texto:
            blocos = texto.split('\n\n')
            for bloco in blocos:
                bloco = bloco.strip()
                if not bloco:
                    continue

                linhas = bloco.split('\n', 1)
                if len(linhas) == 2:
                    # Primeira linha = título da definição (negrito)
                    story.append(Paragraph(
                        f"<b>{linhas[0].strip()}</b>",
                        self.styles['Normal']
                    ))
                    # Resto = conteúdo com quebras de linha preservadas
                    conteudo_html = linhas[1].strip().replace('\n', '<br/>')
                    story.append(Paragraph(
                        conteudo_html,
                        self.styles['Justificado']
                    ))
                else:
                    bloco_html = bloco.replace('\n', '<br/>')
                    story.append(Paragraph(bloco_html, self.styles['Justificado']))

                story.append(Spacer(1, 0.2 * cm))

        story.append(PageBreak())
        return story


    # =================================================================
    # 4. ESTRUTURA DO PGR
    # =================================================================

    def _criar_estrutura_pgr(self):
        """Cria a seção 4 - Estrutura do PGR"""
        nome_empresa = self._get_nome_empresa()
        story = []

        story.append(Paragraph("4. ESTRUTURA DO PGR", self.styles['TituloSecao']))

        sub_secoes = [
            'estrutura_requisitos',
            'estrutura_estrategia',
            'estrutura_registro',
            'estrutura_periodicidade',
            'estrutura_implantacao',
            'estrutura_eficacia',
        ]

        for sub in sub_secoes:
            texto = get_texto_secao(self.pgr, sub, nome_empresa)
            if texto is None:
                continue
            if texto:
                titulo = get_titulo_secao(self.pgr, sub)
                if titulo:
                    story.append(Paragraph(titulo, self.styles['TituloSecao']))
                story.extend(self._texto_para_paragrafos(texto))
                story.append(Spacer(1, 0.3 * cm))

        story.append(PageBreak())
        return story


    # =================================================================
    # 5. RESPONSABILIDADES
    # =================================================================

    def _criar_responsabilidades(self):
        """Cria a seção 5 - Definição das Responsabilidades"""
        nome_empresa = self._get_nome_empresa()
        story = []

        story.append(Paragraph(
            "5. DEFINIÇÃO DAS RESPONSABILIDADES", self.styles['TituloSecao']
        ))

        sub_secoes = [
            'resp_organizacao',
            'resp_informacao',
            'resp_procedimentos',
            'resp_seguranca',
            'resp_cipa',
            'resp_medicina',
            'resp_supervisao',
            'resp_empregados',
        ]

        for sub in sub_secoes:
            texto = get_texto_secao(self.pgr, sub, nome_empresa)
            if texto is None:
                continue
            if texto:
                titulo = get_titulo_secao(self.pgr, sub)
                if titulo:
                    story.append(Paragraph(
                        f"<b>{titulo}</b>", self.styles['Normal']
                    ))
                    story.append(Spacer(1, 0.1 * cm))
                story.extend(self._texto_para_paragrafos(texto))
                story.append(Spacer(1, 0.3 * cm))

        story.append(PageBreak())
        return story


    # =================================================================
    # 6. DIRETRIZES
    # =================================================================

    def _criar_diretrizes(self):
        """Cria a seção 6 - Diretrizes"""
        nome_empresa = self._get_nome_empresa()
        story = []

        story.append(Paragraph("6. DIRETRIZES", self.styles['TituloSecao']))

        # Tenta buscar do banco primeiro a seção principal
        texto_dir = get_texto_secao(self.pgr, 'diretrizes', nome_empresa)
        if texto_dir:
            story.extend(self._texto_para_paragrafos(texto_dir))

        # Sub-seção: Estratégia (Direção, Colaboradores, Recursos)
        texto_est = get_texto_secao(self.pgr, 'diretrizes_estrategia', nome_empresa)
        if texto_est:
            titulo_est = get_titulo_secao(self.pgr, 'diretrizes_estrategia') or 'ESTRATÉGIA'
            story.append(Paragraph(f"<b>{titulo_est}</b>", self.styles['Normal']))
            story.append(Spacer(1, 0.1 * cm))

            # Trata sub-títulos internos (DIREÇÃO, COLABORADORES, RECURSOS)
            blocos = texto_est.split('\n\n')
            for bloco in blocos:
                bloco = bloco.strip()
                if not bloco:
                    continue
                linhas = bloco.split('\n', 1)
                if len(linhas) == 2 and linhas[0].strip().isupper():
                    story.append(Paragraph(
                        f"<b>{linhas[0].strip()}</b>", self.styles['Normal']
                    ))
                    conteudo_html = linhas[1].strip().replace('\n', '<br/>')
                    story.append(Paragraph(conteudo_html, self.styles['Justificado']))
                else:
                    bloco_html = bloco.replace('\n', '<br/>')
                    story.append(Paragraph(bloco_html, self.styles['Justificado']))
                story.append(Spacer(1, 0.2 * cm))
        elif not texto_dir:
            # Fallback hardcoded (mantém o original)
            story.append(Paragraph("<b>ESTRATÉGIA</b>", self.styles['Normal']))
            story.append(Paragraph("<b>DIREÇÃO</b>", self.styles['Normal']))
            story.append(Paragraph(
                f"Este PGR está sendo elaborado pela área de Segurança do "
                f"Trabalho da {nome_empresa} e com apoio operacional para "
                f"implantação.",
                self.styles['Justificado']
            ))
            story.append(Paragraph("<b>COLABORADORES</b>", self.styles['Normal']))
            story.append(Paragraph(
                "Todos os empregados em todos os cargos devem colaborar e "
                "participar de forma efetiva dentro de seu setor de trabalho, "
                "com informações, para que este Programa alcance seus objetivos.",
                self.styles['Justificado']
            ))
            story.append(Paragraph("<b>RECURSOS</b>", self.styles['Normal']))
            story.append(Paragraph(
                "Deverão ser disponibilizados recursos humanos, materiais e "
                "financeiros, para a elaboração e execução do Programa.",
                self.styles['Justificado']
            ))

        story.append(PageBreak())
        return story


    # =================================================================
    # 7. DESENVOLVIMENTO DO PGR
    # =================================================================

    def _criar_desenvolvimento(self):
        """Cria a seção 7 - Desenvolvimento do PGR"""
        nome_empresa = self._get_nome_empresa()
        story = []

        titulo = (
            get_titulo_secao(self.pgr, 'desenvolvimento')
            or '7. DESENVOLVIMENTO DO PGR'
        )
        story.append(Paragraph(titulo, self.styles['TituloSecao']))
        story.append(Paragraph("<b>ETAPAS</b>", self.styles['Normal']))

        texto = get_texto_secao(self.pgr, 'desenvolvimento', nome_empresa)
        if texto:
            story.extend(self._texto_para_paragrafos(texto))

        story.append(PageBreak())
        return story


    # =================================================================
    # 8. METODOLOGIA DE AVALIAÇÃO
    # =================================================================

    def _criar_metodologia(self):
        """Cria a seção 8 - Metodologia de Avaliação"""
        nome_empresa = self._get_nome_empresa()
        story = []

        story.append(Paragraph(
            "8. METODOLOGIA DE AVALIAÇÃO", self.styles['TituloSecao']
        ))

        texto_intro = (
            self.pgr.metodologia_avaliacao
            or get_texto_secao(self.pgr, 'metodologia_avaliacao', nome_empresa)
        )
        if texto_intro:
            story.extend(self._texto_para_paragrafos(texto_intro))
            story.append(Spacer(1, 0.3 * cm))

        agentes = [
            'metodo_ruido',
            'metodo_calor',
            'metodo_quimico',
            'metodo_biologico',
            'metodo_ergonomico',
            'metodo_mecanico',
        ]

        for agente in agentes:
            texto = get_texto_secao(self.pgr, agente, nome_empresa)
            if texto is None:
                continue
            if texto:
                titulo = get_titulo_secao(self.pgr, agente)
                if titulo:
                    story.append(Paragraph(
                        f"<b>{titulo}</b>", self.styles['Normal']
                    ))
                story.extend(self._texto_para_paragrafos(texto))
                story.append(Spacer(1, 0.3 * cm))

        story.append(PageBreak())
        return story


    # =================================================================
    # 9. INVENTÁRIO DE RISCOS
    # =================================================================

    def _criar_inventario_riscos(self):
        """Cria o inventário de riscos conforme PDF modelo oficial (seção 16)"""
        story = []
        story.append(Paragraph(
            "16. LEVANTAMENTO DOS RISCOS",
            self.styles['TituloSecao']
        ))
        story.append(Paragraph(
            "RISCOS AMBIENTAIS E OCUPACIONAIS", self.styles['SubtituloCapa']
        ))
        story.append(Spacer(1, 0.5 * cm))

        grupos_ges = self.pgr.grupos_exposicao.filter(
            ativo=True
        ).order_by('codigo')

        if not grupos_ges.exists():
            story.append(Paragraph(
                "Nenhum Grupo de Exposição Similar (GES) cadastrado.",
                self.styles['Normal']
            ))
            story.append(PageBreak())
            return story

        for ges in grupos_ges:
            local_nome = (
                self.local_prestacao.razao_social
                if self.local_prestacao else 'N/A'
            )
            dept_nome = (
                ges.ambiente_trabalho.nome
                if ges.ambiente_trabalho else 'N/A'
            )

            info_data = [
                ['LOCAL:', local_nome],
                ['DEPARTAMENTO:', dept_nome],
            ]

            if (ges.ambiente_trabalho
                    and ges.ambiente_trabalho.caracteristicas):
                info_data.append([
                    'DESCRIÇÃO DO\nAMBIENTE DE TRABALHO:',
                    ges.ambiente_trabalho.caracteristicas
                ])

            cargo_info = ges.cargo.nome if ges.cargo else 'N/A'
            num_trab = ges.numero_trabalhadores or '0'
            info_data.append([
                'CARGO/FUNÇÃO\nANALISADA:',
                f"{num_trab} – {cargo_info}"
            ])
            info_data.append([
                'JORNADA DE TRABALHO:',
                ges.jornada_trabalho or '44 horas semanais'
            ])
            info_data.append([
                'HORÁRIO DE TRABALHO:',
                ges.horario_trabalho or 'N/A'
            ])
            info_data.append([
                'DESCRIÇÃO DAS\nATIVIDADES:',
                ges.descricao_atividades or 'N/A'
            ])

            table_info = Table(info_data, colWidths=[4.5 * cm, 12 * cm])
            table_info.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1),
                 colors.Color(0.93, 0.93, 0.93)),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(table_info)
            story.append(Spacer(1, 0.4 * cm))

            story.append(Paragraph(
                "<b>ANTECIPAÇÃO E RECONHECIMENTO DOS RISCOS E "
                "AVALIAÇÃO DOS AGENTES</b>",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 0.2 * cm))

            riscos = ges.riscos.select_related(
                'tipo_risco'
            ).order_by('tipo_risco__categoria', 'agente')

            if riscos.exists():
                header_row = [
                    Paragraph('<b>RISCO</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>AGENTE</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>FONTE<br/>GERADORA</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>PERFIL DA<br/>EXPOSIÇÃO</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>MEIO DE<br/>PROPAGAÇÃO</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>POSSÍVEIS<br/>EFEITOS<br/>À SAÚDE</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>GRAVIDADE</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>EXPOSIÇÃO</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>SEVERIDADE</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>PROBABILIDADE</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>CLASSIFICAÇÃO<br/>DO RISCO</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>MÉTODO<br/>UTILIZADO</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>CONTROLE<br/>DO RISCO</b>', self.styles['TabelaTitulo']),
                ]
                dados_riscos = [header_row]

                for risco in riscos:
                    perfil_display = risco.get_perfil_exposicao_display()
                    if ' - ' in perfil_display:
                        perfil_display = perfil_display.split(' - ')[0]

                    metodo = (
                        risco.get_metodo_avaliacao_display()
                        if hasattr(risco, 'get_metodo_avaliacao_display')
                        else 'Qualitativo'
                    )
                    

                    dados_riscos.append([
                        Paragraph(
                            risco.tipo_risco.get_categoria_display().upper(),
                            self.styles['TabelaTexto']
                        ),
                        Paragraph(
                            risco.agente or '-', self.styles['TabelaTexto']
                        ),
                        Paragraph(
                            risco.fonte_geradora or '-',
                            self.styles['TabelaTexto']
                        ),
                        Paragraph(
                            perfil_display, self.styles['TabelaTexto']
                        ),
                        Paragraph(
                            risco.meio_propagacao or '-',
                            self.styles['TabelaTexto']
                        ),
                        Paragraph(
                            risco.possiveis_efeitos_saude or '-',
                            self.styles['TabelaTexto']
                        ),
                        Paragraph(
                            str(risco.gravidade_g),
                            self.styles['TabelaTextoCentro']
                        ),
                        Paragraph(
                            str(risco.exposicao_e),
                            self.styles['TabelaTextoCentro']
                        ),
                        Paragraph(
                            str(risco.severidade_s),
                            self.styles['TabelaTextoCentro']
                        ),
                        Paragraph(
                            str(risco.probabilidade_p),
                            self.styles['TabelaTextoCentro']
                        ),
                        Paragraph(
                            risco.get_classificacao_risco_display(),
                            self.styles['TabelaTexto']
                        ),
                        Paragraph(metodo, self.styles['TabelaTexto']),
                        Paragraph(
                            risco.medidas_controle_existentes or '-',
                            self.styles['TabelaTexto']
                        ),
                    ])

                col_widths = [
                    1.1 * cm, 1.5 * cm, 1.5 * cm, 1.2 * cm, 1.1 * cm,
                    1.8 * cm, 0.9 * cm, 0.9 * cm, 0.9 * cm, 0.9 * cm,
                    1.3 * cm, 1.1 * cm, 2.4 * cm,
                ]

                table_riscos = Table(
                    dados_riscos, colWidths=col_widths, repeatRows=1
                )
                table_riscos.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0),
                     colors.HexColor('#003366')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTSIZE', (0, 0), (-1, -1), 6),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                     [colors.white, colors.Color(0.95, 0.95, 0.95)]),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 2),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(table_riscos)
            else:
                story.append(Paragraph(
                    "<i>Nenhum risco identificado para este GES.</i>",
                    self.styles['Normal']
                ))

            story.append(Spacer(1, 0.4 * cm))

            # ═════════════════════════════════════════════════════
            # AVALIAÇÕES QUANTITATIVAS (tabela formatada)
            # ═════════════════════════════════════════════════════
            avaliacoes = []
            for risco in riscos:
                for av in risco.avaliacoes_quantitativas.all():
                    avaliacoes.append(av)

            if avaliacoes:
                story.append(Spacer(1, 0.3 * cm))
                story.append(Paragraph(
                    "<b>AVALIAÇÕES QUANTITATIVAS</b>",
                    self.styles['Normal']
                ))
                story.append(Spacer(1, 0.2 * cm))

                # ── Agrupar por tipo de avaliação ──
                avaliacoes_por_tipo = {}
                for av in avaliacoes:
                    tipo = av.get_tipo_avaliacao_display()
                    if tipo not in avaliacoes_por_tipo:
                        avaliacoes_por_tipo[tipo] = []
                    avaliacoes_por_tipo[tipo].append(av)

                # ── Header da tabela ──
                header_row = [
                    Paragraph('<b>TIPO</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>RESULTADO</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>UNIDADE</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>DATA</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>CONFORMIDADE</b>', self.styles['TabelaTitulo']),
                    Paragraph('<b>EQUIPAMENTO</b>', self.styles['TabelaTitulo']),
                ]
                dados_avaliacoes = [header_row]

                for tipo_nome, lista_av in avaliacoes_por_tipo.items():
                    for av in lista_av:
                        conformidade_texto = 'Conforme' if av.conforme else 'Não Conforme'

                        # Estilo condicional para conformidade
                        if av.conforme:
                            conf_style = ParagraphStyle(
                                'ConfOk',
                                parent=self.styles['TabelaTextoCentro'],
                                textColor=colors.HexColor('#198754'),
                                fontName='Helvetica-Bold',
                            )
                        else:
                            conf_style = ParagraphStyle(
                                'ConfNao',
                                parent=self.styles['TabelaTextoCentro'],
                                textColor=colors.HexColor('#dc3545'),
                                fontName='Helvetica-Bold',
                            )

                        # Unidade legível
                        unidade = av.unidade_medida or ''
                        if hasattr(av, 'get_unidade_medida_display'):
                            unidade = av.get_unidade_medida_display()

                        dados_avaliacoes.append([
                            Paragraph(
                                f"<b>{tipo_nome}</b>",
                                self.styles['TabelaTexto']
                            ),
                            Paragraph(
                                f"{av.resultado_medido}",
                                self.styles['TabelaTextoCentro']
                            ),
                            Paragraph(
                                unidade,
                                self.styles['TabelaTextoCentro']
                            ),
                            Paragraph(
                                av.data_avaliacao.strftime('%d/%m/%Y'),
                                self.styles['TabelaTextoCentro']
                            ),
                            Paragraph(conformidade_texto, conf_style),
                            Paragraph(
                                av.equipamento_utilizado or 'N/A',
                                self.styles['TabelaTexto']
                            ),
                        ])

                # ── Montar a tabela ──
                col_widths_av = [
                    2.2 * cm,   # Tipo
                    2.0 * cm,   # Resultado
                    1.8 * cm,   # Unidade
                    2.0 * cm,   # Data
                    2.2 * cm,   # Conformidade
                    6.3 * cm,   # Equipamento
                ]

                table_avaliacoes = Table(
                    dados_avaliacoes,
                    colWidths=col_widths_av,
                    repeatRows=1
                )
                table_avaliacoes.setStyle(TableStyle([
                    # Header
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

                    # Grid
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

                    # Zebra
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                     [colors.white, colors.Color(0.95, 0.95, 0.95)]),

                    # Padding
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ]))

                # Destaque vermelho para "Não Conforme" (fundo da célula)
                for row_idx, av in enumerate(avaliacoes, 1):
                    if not av.conforme:
                        table_avaliacoes.setStyle(TableStyle([
                            ('BACKGROUND', (4, row_idx), (4, row_idx),
                             colors.Color(1.0, 0.9, 0.9)),  # Rosa claro
                        ]))

                story.append(table_avaliacoes)
                story.append(Spacer(1, 0.3 * cm))


        return story

    # =================================================================
    # 10. PLANO DE AÇÃO (texto)
    # =================================================================

    def _criar_plano_acao_texto(self):
        """Cria a seção 10 - Plano de Ação (texto introdutório)"""
        nome_empresa = self._get_nome_empresa()
        story = []

        titulo = get_titulo_secao(self.pgr, 'plano_acao') or '10. PLANO DE AÇÃO'
        story.append(Paragraph(titulo, self.styles['TituloSecao']))

        texto = get_texto_secao(self.pgr, 'plano_acao', nome_empresa)
        if texto:
            story.extend(self._texto_para_paragrafos(texto))

        # Documentação (sub-seção nova)
        texto_doc = get_texto_secao(self.pgr, 'plano_acao_documentacao', nome_empresa)
        if texto_doc:
            titulo_doc = get_titulo_secao(self.pgr, 'plano_acao_documentacao') or 'DOCUMENTAÇÃO'
            story.append(Paragraph(f"<b>{titulo_doc}</b>", self.styles['Normal']))
            story.append(Spacer(1, 0.1 * cm))
            story.extend(self._texto_para_paragrafos(texto_doc))

        story.append(PageBreak())
        return story


    # =================================================================
    # 11. MEDIDAS DE PROTEÇÃO
    # =================================================================

    def _criar_medidas_protecao(self):
        """Cria a seção 11 - Medidas de Proteção (completa conforme PDF modelo)"""
        nome_empresa = self._get_nome_empresa()
        story = []

        story.append(Paragraph(
            "11. MEDIDAS DE PROTEÇÃO", self.styles['TituloSecao']
        ))

        sub_secoes = [
            'medidas_epc',
            'medidas_administrativas',
            'medidas_epi',
            'medidas_uso_epi',
            'medidas_substituicao_epi',
            'medidas_protecao_geral',
            'medidas_monitoramento',
            'medidas_registro_divulgacao',
        ]

        for sub in sub_secoes:
            texto = get_texto_secao(self.pgr, sub, nome_empresa)
            if texto is None:
                continue
            if texto:
                titulo = get_titulo_secao(self.pgr, sub)
                if titulo:
                    story.append(Paragraph(
                        f"<b>{titulo}</b>", self.styles['Normal']
                    ))
                    story.append(Spacer(1, 0.1 * cm))
                story.extend(self._texto_para_paragrafos(texto))
                story.append(Spacer(1, 0.3 * cm))

        # ═════════════════════════════════════════════════════
        # RECOMENDAÇÃO ESPECIAL (EPI) — Texto + Ficha visual
        # ═════════════════════════════════════════════════════
        story.extend(self._criar_ficha_epi())

        story.append(PageBreak())
        return story

    # =================================================================
    # FICHA DE CONTROLE DE EPIs (modelo visual)
    # =================================================================

    def _criar_ficha_epi(self):
        """
        Cria a Ficha de Controle de EPIs conforme modelo oficial do PGR.
        Renderiza em página separada para evitar cortes.
        """
        nome_empresa = self._get_nome_empresa()
        story = []

        # ── PÁGINA SEPARADA para a ficha ──
        story.append(PageBreak())

        # ── Título da sub-seção ──
        titulo_epi = get_titulo_secao(
            self.pgr, 'medidas_recomendacao_epi'
        ) or 'RECOMENDAÇÃO ESPECIAL (EPI)'
        story.append(Paragraph(
            f"<b>{titulo_epi}</b>", self.styles['Normal']
        ))
        story.append(Spacer(1, 0.1 * cm))

        # ── Texto introdutório ──
        story.append(Paragraph(
            'Deverá ser utilizada a "Ficha de Controle de EPIs – Equipamentos de '
            'Proteção Individual", conforme determinação de ordem legal (modelo '
            'abaixo), para registro de 1ª (primeira) dotação e substituição dos '
            'EPIs (Equipamentos de Proteção Individual) quando necessário, em '
            'função dos riscos existentes no ambiente de trabalho.',
            self.styles['Justificado']
        ))
        story.append(Spacer(1, 0.3 * cm))

        # ═══════════════════════════════════════════════
        # FICHA INTEIRA dentro de KeepTogether
        # ═══════════════════════════════════════════════
        ficha_elements = []

        # ── Estilos específicos da ficha ──
        estilo_ficha_titulo = ParagraphStyle(
            'FichaTitulo',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            alignment=TA_CENTER,
            leading=14,
        )
        estilo_ficha_subtitulo = ParagraphStyle(
            'FichaSubtitulo',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            alignment=TA_CENTER,
            leading=12,
        )
        estilo_ficha_label = ParagraphStyle(
            'FichaLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
        )
        estilo_ficha_texto = ParagraphStyle(
            'FichaTexto',
            parent=self.styles['Normal'],
            fontSize=7.5,
            leading=10,
            alignment=TA_JUSTIFY,
        )
        estilo_ficha_campo = ParagraphStyle(
            'FichaCampo',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
        )

        # ── CABEÇALHO ──
        header_ficha = Table(
            [[
                Paragraph('<b>FICHA DE CONTROLE DE EPIs</b>', estilo_ficha_titulo),
                Paragraph('Folha nº', estilo_ficha_campo),
            ]],
            colWidths=[12 * cm, 4 * cm]
        )
        header_ficha.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        ficha_elements.append(header_ficha)

        # ── DADOS DE IDENTIFICAÇÃO ──
        ficha_elements.append(Table(
            [[Paragraph('<b>Dados de Identificação</b>', estilo_ficha_label)]],
            colWidths=[16 * cm]
        ))

        dados_id = [
            [
                Paragraph('Empregado:', estilo_ficha_campo),
                '', '', '',
            ],
            [
                Paragraph('Cargo:', estilo_ficha_campo),
                '',
                Paragraph('Registro:', estilo_ficha_campo),
                '',
            ],
            [
                Paragraph('Admissão:___/___/____', estilo_ficha_campo),
                Paragraph('Demissão:____/____/____', estilo_ficha_campo),
                Paragraph('Contrato:', estilo_ficha_campo),
                '',
            ],
        ]

        table_id = Table(dados_id, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
        table_id.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('SPAN', (1, 0), (3, 0)),
        ]))
        ficha_elements.append(table_id)

        # ── TERMO DE COMPROMISSO ──
        ficha_elements.append(Spacer(1, 0.15 * cm))
        ficha_elements.append(Paragraph(
            '<b>TERMO DE COMPROMISSO</b>', estilo_ficha_subtitulo
        ))
        ficha_elements.append(Spacer(1, 0.1 * cm))

        ficha_elements.append(Paragraph(
            f'Eu, _____________________________________________________________, '
            f'declaro que recebi de <b>{nome_empresa}</b>, os Equipamentos de '
            f'Proteção Individual – EPIs abaixo relacionados, comprometendo-me a:',
            estilo_ficha_texto
        ))

        itens_compromisso = [
            (
                f'1) Usá-los em trabalho, zelando pela sua guarda, conservação e bom uso, '
                f'devolvendo-os quando se tornarem impróprios para o uso e/ou meu '
                f'desligamento da {nome_empresa} ou do seu respectivo contrato;'
            ),
            (
                '2) Em caso de perda, mau uso, extravio ou inutilização proposital do EPI '
                'recebido, assumir a responsabilidade quanto à restituição do seu valor '
                'atualizado, conforme autorização de débito por mim assinada.'
            ),
        ]
        for item in itens_compromisso:
            ficha_elements.append(Paragraph(item, estilo_ficha_texto))

        ficha_elements.append(Spacer(1, 0.1 * cm))
        ficha_elements.append(Paragraph(
            'Declaro ainda ter recebido no ato de minha admissão e no ato do recebimento:',
            estilo_ficha_texto
        ))

        declaracoes = [
            '1) Treinamento básico e instruções prévias sobre a forma de utilização e guarda dos EPIs recebido;',
            '2) Instruções sobre os riscos a que estou exposto em minha área de trabalho, bem como sua prevenção;',
            '3) Estou ciente de que o não uso dos EPIs, constitui ato faltoso conforme artigo 158 da CLT.',
        ]
        for decl in declaracoes:
            ficha_elements.append(Paragraph(decl, estilo_ficha_texto))

        ficha_elements.append(Spacer(1, 0.1 * cm))
        ficha_elements.append(Paragraph(
            'Local e data:________________________________    '
            'Assinatura:_________________________',
            estilo_ficha_campo
        ))
        ficha_elements.append(Spacer(1, 0.2 * cm))

        # ── TABELA RECEBIMENTO / DEVOLUÇÃO ──
        ts_ficha = ParagraphStyle(
            'FichaTabelaHeader',
            parent=self.styles['Normal'],
            fontSize=7,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            leading=9,
        )

        header_rec_dev = [
            '', '',
            Paragraph('<b>RECEBIMENTO</b>', ts_ficha),
            '', '', '',
            Paragraph('<b>DEVOLUÇÃO</b>', ts_ficha),
            '',
        ]

        header_colunas = [
            Paragraph('<b>Data</b>', ts_ficha),
            Paragraph('<b>Qtde.</b>', ts_ficha),
            Paragraph('<b>Un.</b>', ts_ficha),
            Paragraph('<b>Descrição EPI</b>', ts_ficha),
            Paragraph('<b>Certificado<br/>Aprovação</b>', ts_ficha),
            Paragraph('<b>Visto<br/>Recebimento</b>', ts_ficha),
            Paragraph('<b>Data</b>', ts_ficha),
            Paragraph('<b>Recebedor</b>', ts_ficha),
        ]

        dados_tabela_epi = [header_rec_dev, header_colunas]

        # 6 linhas vazias (cabe melhor numa página)
        for _ in range(6):
            dados_tabela_epi.append([''] * 8)

        col_widths_epi = [
            1.3 * cm, 1.0 * cm, 0.8 * cm, 4.5 * cm,
            2.0 * cm, 1.8 * cm, 1.3 * cm, 3.3 * cm,
        ]

        table_epi = Table(dados_tabela_epi, colWidths=col_widths_epi)
        table_epi.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.93, 0.93, 0.93)),
            ('SPAN', (0, 0), (1, 0)),
            ('SPAN', (2, 0), (5, 0)),
            ('SPAN', (6, 0), (7, 0)),
            ('BACKGROUND', (0, 1), (-1, 1), colors.Color(0.93, 0.93, 0.93)),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LINEAFTER', (5, 0), (5, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 1), 4),
            ('TOPPADDING', (0, 2), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 2), (-1, -1), 7),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
        ]))
        ficha_elements.append(table_epi)

        # ── Envolver tudo num KeepTogether ──
        story.append(KeepTogether(ficha_elements))

        story.append(Spacer(1, 0.4 * cm))

        # ═══════════════════════════════════════════════
        # CLT (fora do KeepTogether, logo abaixo)
        # ═══════════════════════════════════════════════
        estilo_clt = ParagraphStyle(
            'CLTTexto',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=11,
        )

        story.append(Paragraph(
            '<b>CONSOLIDAÇÃO DAS LEIS DO TRABALHO – CLT</b>', estilo_clt
        ))
        story.append(Paragraph(
            '<b>Art. 158</b> – Cabe aos empregados', estilo_clt
        ))
        story.append(Paragraph(
            'I – Observar as normas de segurança e medicina do trabalho, inclusive '
            'as instruções de que trata o item II do artigo anterior;', estilo_clt
        ))
        story.append(Paragraph(
            'II – Colaborar com a empresa na aplicação dos dispositivos deste capítulo.',
            estilo_clt
        ))
        story.append(Paragraph(
            '<b>Parágrafo Único:</b> Constitui ato faltoso do empregado a recusa '
            'injustificada:', estilo_clt
        ))
        story.append(Paragraph('a)...', estilo_clt))
        story.append(Paragraph(
            'b) ao uso dos equipamentos de proteção individual fornecidos pela empresa.',
            estilo_clt
        ))

        return story

    # =================================================================
    # 12. CRONOGRAMA DE AÇÕES
    # =================================================================

    def _criar_cronograma_acoes(self):
        """Cria a seção de cronograma de ações conforme modelo oficial"""
        story = []
        story.append(Paragraph(
            "12. CRONOGRAMA DE AÇÕES", self.styles['TituloSecao']
        ))
        story.append(Spacer(1, 0.3 * cm))

        dados_cronograma = [[
            Paragraph('<b>ITEM</b>', self.styles['TabelaTitulo']),
            Paragraph('<b>AÇÕES NECESSÁRIAS</b>', self.styles['TabelaTitulo']),
            Paragraph('<b>PÚBLICO ALVO</b>', self.styles['TabelaTitulo']),
            Paragraph('<b>REALIZAÇÃO</b>', self.styles['TabelaTitulo']),
            Paragraph(
                '<b>PRÓXIMA<br/>AVALIAÇÃO/REVISÃO</b>',
                self.styles['TabelaTitulo']
            ),
        ]]

        acoes = self.pgr.cronograma_acoes.all().order_by('numero_item')

        if acoes.exists():
            for acao in acoes:
                realizacao = (
                    acao.get_periodicidade_display()
                    if hasattr(acao, 'get_periodicidade_display')
                    else 'N/A'
                )
                prox_avaliacao = (
                    acao.data_proxima_avaliacao.strftime('%m/%Y')
                    if acao.data_proxima_avaliacao else 'N/A'
                )

                dados_cronograma.append([
                    Paragraph(
                        f"{acao.numero_item:02d}",
                        self.styles['TabelaTextoCentro']
                    ),
                    Paragraph(
                        acao.acao_necessaria or '',
                        self.styles['TabelaTexto']
                    ),
                    Paragraph(
                        acao.publico_alvo or 'Todos os colaboradores',
                        self.styles['TabelaTexto']
                    ),
                    Paragraph(realizacao, self.styles['TabelaTexto']),
                    Paragraph(
                        prox_avaliacao, self.styles['TabelaTextoCentro']
                    ),
                ])
        else:
            dados_cronograma.append([
                Paragraph("-", self.styles['TabelaTextoCentro']),
                Paragraph(
                    "Nenhuma ação cadastrada", self.styles['TabelaTexto']
                ),
                Paragraph("-", self.styles['TabelaTexto']),
                Paragraph("-", self.styles['TabelaTexto']),
                Paragraph("-", self.styles['TabelaTextoCentro']),
            ])

        table_cronograma = Table(
            dados_cronograma,
            colWidths=[1.2 * cm, 6.5 * cm, 3 * cm, 3 * cm, 2.8 * cm],
            repeatRows=1
        )
        table_cronograma.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(table_cronograma)
        story.append(Paragraph(
            "CM = contrato de manutenção.\n\n"
        ))
        story.append(PageBreak())
        return story

    # =================================================================
    # 13. DIVULGAÇÃO DO PROGRAMA
    # =================================================================

    def _criar_divulgacao(self):
        """Cria a seção 13 - Divulgação do Programa"""
        nome_empresa = self._get_nome_empresa()
        story = []

        # Título
        titulo = get_titulo_secao(self.pgr, 'divulgacao')
        if not titulo:
            titulo = '13. DIVULGAÇÃO DO PROGRAMA'
        story.append(Paragraph(titulo, self.styles['TituloSecao']))

        # Texto do banco
        texto = get_texto_secao(self.pgr, 'divulgacao', nome_empresa)

        # Fallback hardcoded
        if not texto or not texto.strip():
            texto = (
                'Os documentos e os procedimentos operacionais que integram o Programa de '
                'Gerenciamento de Risco (PGR) estarão disponíveis aos empregados.\n\n'
                'A atualização do PGR será realizada quando da ocorrência de alterações '
                'significativas de ordem tecnológica, operacional, legal ou regulatória que '
                'provoquem a necessidade de adequação dos documentos que o integram ou ainda '
                'quando for recomendado na auditoria anual.\n\n'
                'Cabe aos responsáveis pelas respectivas áreas procederem a divulgação das '
                'atualizações dos documentos que integram o PGR, após as devidas aprovações, '
                'respeitadas eventuais restrições para o manuseio e circulação quando se tratarem '
                'de documentos controlados.\n\n'
                'Esses dados foram levantados por profissionais do departamento de QHSE '
                '(Qualidade, Saúde, Segurança e Meio Ambiente) com a participação dos responsáveis '
                'pelas áreas analisadas, designados de CIPA e dos próprios trabalhadores e '
                'inseridos no Inventário de Riscos deste PGR.'
            )

        # DEBUG temporário — remova depois
        print(f"[DEBUG PDF] _criar_divulgacao: texto tem {len(texto)} chars")

        story.extend(self._texto_para_paragrafos(texto))
        story.append(PageBreak())
        return story

    # =================================================================
    # 14. RECOMENDAÇÕES GERAIS
    # =================================================================

    def _criar_recomendacoes(self):
        """Cria a seção 14 - Recomendações Gerais"""
        nome_empresa = self._get_nome_empresa()
        story = []

        # Título
        titulo = get_titulo_secao(self.pgr, 'recomendacoes')
        if not titulo:
            titulo = '14. RECOMENDAÇÕES GERAIS'
        story.append(Paragraph(titulo, self.styles['TituloSecao']))

        # Texto do banco
        texto = get_texto_secao(self.pgr, 'recomendacoes', nome_empresa)

        # Fallback hardcoded
        if not texto or not texto.strip():
            texto = (
                '- Aplicação de medidas, sempre que necessárias, de caráter administrativo ou da '
                'organização do trabalho;\n'
                '- Aplicação de Treinamento de Segurança em geral, sobre Uso de EPI, Cuidados com '
                'produtos químicos, Levantamento de peso e Trabalho em Altura, assim como outros '
                'treinamentos que se fizerem necessários;\n'
                '- Aplicação de Treinamento para membro designado de segurança da CIPA, no setor, '
                'em cumprimento com a portaria 3214 de 08/06/78 – NR 05;\n'
                '- Dotação de creme protetor para as mãos para os funcionários que tiverem contato '
                'direto com graxas, óleos e outros produtos químicos durante a jornada de trabalho;\n'
                '- Fornecimento de EPIs adequados de acordo com Ficha Técnica de Classificação de '
                'EPI por Função;\n'
                '- Orientações sobre o uso correto e higiênico dos vestiários e asseio pessoal;\n'
                '- Execução do Gerenciamento de Riscos através da observação de segurança e uso '
                'dos EPIs;\n'
                '- Guarda de documentação do controle das intervenções de segurança do trabalho;\n'
                '- Aplicação de rígido controle médico dos empregados.'
            )

        # DEBUG temporário — remova depois
        print(f"[DEBUG PDF] _criar_recomendacoes: texto tem {len(texto)} chars")

        story.extend(self._texto_para_paragrafos(texto))
        story.append(PageBreak())
        return story


    # =================================================================
    # 15. LEGISLAÇÃO
    # =================================================================

    def _criar_legislacao(self):
        """Cria a seção 15 - Legislação Aplicável"""
        nome_empresa = self._get_nome_empresa()
        story = []

        titulo = get_titulo_secao(self.pgr, 'legislacao')
        if not titulo:
            titulo = '15. LEGISLAÇÃO APLICÁVEL'
        story.append(Paragraph(titulo, self.styles['TituloSecao']))

        texto = get_texto_secao(self.pgr, 'legislacao', nome_empresa)

        if not texto or not texto.strip():
            texto = (
                '- NR 01 – Disposições Gerais e Gerenciamento de Riscos Ocupacionais;\n'
                '- NR 04 – Serviços Especializados em Engenharia de Segurança e em Medicina do Trabalho;\n'
                '- NR 05 – Comissão Interna de Prevenção de Acidentes;\n'
                '- NR 06 – Equipamentos de Proteção Individual – EPI;\n'
                '- NR 07 – Programa de Controle Médico de Saúde Ocupacional;\n'
                '- NR 09 – Avaliação e Controle das Exposições Ocupacionais a Agentes Físicos, '
                'Químicos e Biológicos;\n'
                '- NR 15 – Atividades e Operações Insalubres;\n'
                '- NR 16 – Atividades e Operações Perigosas;\n'
                '- NR 17 – Ergonomia;\n'
                '- Demais Normas Regulamentadoras aplicáveis às atividades da empresa.'
            )

        story.extend(self._texto_para_paragrafos(texto))
        story.append(PageBreak())
        return story
    
    # =================================================================
    # 16. LEVANTAMENTO DOS RISCOS (Inventário por GES)
    # =================================================================

    def _criar_inventario_riscos(self):
        """Cria o inventário de riscos conforme PDF modelo oficial (seção 16)"""
        story = []

        # Cor padrão do cabeçalho (azul escuro do modelo)
        AZUL_ESCURO = colors.HexColor('#003366')
        AZUL_CLARO = colors.HexColor('#D6E4F0')
        CINZA_ZEBRA = colors.Color(0.95, 0.95, 0.95)

        # Largura útil do frame
        largura_util = A4[0] - 3 * cm  # 1.5cm cada margem

        grupos_ges = self.pgr.grupos_exposicao.filter(
            ativo=True
        ).order_by('codigo')

        if not grupos_ges.exists():
            story.append(Paragraph(
                "16. LEVANTAMENTO DOS RISCOS",
                self.styles['TituloSecao']
            ))
            story.append(Paragraph(
                "Nenhum Grupo de Exposição Similar (GES) cadastrado.",
                self.styles['Normal']
            ))
            story.append(PageBreak())
            return story

        for idx, ges in enumerate(grupos_ges):
            # ─── Título da seção (só no primeiro GES) ───
            if idx == 0:
                story.append(Paragraph(
                    "16. LEVANTAMENTO DOS RISCOS",
                    self.styles['TituloSecao']
                ))
                story.append(Spacer(1, 0.3 * cm))

            # ═══════════════════════════════════════════════
            # CABEÇALHO DO GES (estilo PDF modelo)
            # ═══════════════════════════════════════════════

            local_nome = (
                self.local_prestacao.razao_social
                if self.local_prestacao else 'N/A'
            )
            dept_nome = (
                ges.ambiente_trabalho.nome
                if ges.ambiente_trabalho else 'Manutenção'
            )
            desc_ambiente = ''
            if ges.ambiente_trabalho and ges.ambiente_trabalho.caracteristicas:
                desc_ambiente = ges.ambiente_trabalho.caracteristicas

            # Número de trabalhadores + gênero + cargo
            cargo_nome = ges.cargo.nome if ges.cargo else (
                ges.funcao.nome if ges.funcao else 'N/A'
            )
            num_trab = ges.numero_trabalhadores or 0
            num_trab_texto = f"{num_trab:02d}" if num_trab < 10 else str(num_trab)
            cargo_texto = f"{num_trab_texto} – {cargo_nome}"

            # Estilo para labels (coluna esquerda)
            style_label = ParagraphStyle(
                'InfoLabel',
                parent=self.styles['Normal'],
                fontSize=7,
                fontName='Helvetica-Bold',
                textColor=colors.white,
                leading=9,
            )
            # Estilo para valores (coluna direita)
            style_valor = ParagraphStyle(
                'InfoValor',
                parent=self.styles['Normal'],
                fontSize=7,
                fontName='Helvetica',
                leading=9,
            )

            # Montar dados do cabeçalho
            info_rows = [
                [
                    Paragraph('LOCAL:', style_label),
                    Paragraph(local_nome, style_valor),
                ],
                [
                    Paragraph('DEPARTAMENTO:', style_label),
                    Paragraph(dept_nome, style_valor),
                ],
            ]

            if desc_ambiente:
                info_rows.append([
                    Paragraph('DESCRIÇÃO DO<br/>AMBIENTE DE TRABALHO:', style_label),
                    Paragraph(desc_ambiente, style_valor),
                ])

            info_rows.extend([
                [
                    Paragraph('CARGO/FUNÇÃO<br/>ANALISADA:', style_label),
                    Paragraph(cargo_texto, style_valor),
                ],
                [
                    Paragraph('JORNADA DE TRABALHO:', style_label),
                    Paragraph(ges.jornada_trabalho or '44 horas semanais', style_valor),
                ],
                [
                    Paragraph('HORÁRIO DE TRABALHO:', style_label),
                    Paragraph(ges.horario_trabalho or 'N/A', style_valor),
                ],
                [
                    Paragraph('DESCRIÇÃO DAS<br/>ATIVIDADES:', style_label),
                    Paragraph(ges.descricao_atividades or 'N/A', style_valor),
                ],
            ])

            col_label = 4.5 * cm
            col_valor = largura_util - col_label

            table_info = Table(info_rows, colWidths=[col_label, col_valor])
            table_info.setStyle(TableStyle([
                # Fundo azul nos labels
                ('BACKGROUND', (0, 0), (0, -1), AZUL_ESCURO),
                # Fundo claro nos valores
                ('BACKGROUND', (1, 0), (1, -1), AZUL_CLARO),
                # Texto
                ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
                # Alinhamento
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                # Padding
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(table_info)
            story.append(Spacer(1, 0.3 * cm))

            # ═══════════════════════════════════════════════
            # SUBTÍTULO: ANTECIPAÇÃO E RECONHECIMENTO
            # ═══════════════════════════════════════════════

            subtitulo_style = ParagraphStyle(
                'SubtituloRiscos',
                parent=self.styles['Normal'],
                fontSize=7,
                fontName='Helvetica-Bold',
                textColor=AZUL_ESCURO,
                spaceAfter=4,
            )
            story.append(Paragraph(
                "ANTECIPAÇÃO E RECONHECIMENTO DOS RISCOS E AVALIAÇÃO DOS AGENTES",
                subtitulo_style
            ))
            story.append(Spacer(1, 0.2 * cm))

            # ═══════════════════════════════════════════════
            # TABELA DE RISCOS
            # ═══════════════════════════════════════════════

            riscos = ges.riscos.select_related(
                'tipo_risco'
            ).order_by('tipo_risco__categoria', 'agente')

            if riscos.exists():
                # Estilos específicos para a tabela de riscos
                style_th = ParagraphStyle(
                    'RiscoTH',
                    parent=self.styles['Normal'],
                    fontSize=5.5,
                    fontName='Helvetica-Bold',
                    textColor=colors.white,
                    alignment=1,  # CENTER
                    leading=7,
                )
                style_td = ParagraphStyle(
                    'RiscoTD',
                    parent=self.styles['Normal'],
                    fontSize=6,
                    fontName='Helvetica',
                    leading=7.5,
                )
                style_td_center = ParagraphStyle(
                    'RiscoTDCenter',
                    parent=style_td,
                    alignment=1,  # CENTER
                )

                header_row = [
                    Paragraph('RISCO', style_th),
                    Paragraph('AGENTE', style_th),
                    Paragraph('FONTE<br/>GERADORA', style_th),
                    Paragraph('PERFIL DA<br/>EXPOSIÇÃO', style_th),
                    Paragraph('MEIO DE<br/>PROPAGAÇÃO', style_th),
                    Paragraph('POSSÍVEIS<br/>EFEITOS<br/>À SAÚDE', style_th),
                    Paragraph('GRAVI<br/>DADE', style_th),
                    Paragraph('EXPO<br/>SIÇÃO', style_th),
                    Paragraph('SEVERI<br/>DADE', style_th),
                    Paragraph('PROBA<br/>BILIDADE', style_th),
                    Paragraph('CLASSIFI<br/>CAÇÃO DO<br/>RISCO', style_th),
                    Paragraph('MÉTODO<br/>UTILIZADO', style_th),
                    Paragraph('CONTROLE DO RISCO', style_th),
                ]
                dados_riscos = [header_row]

                for risco in riscos:
                    # Perfil sem o número
                    perfil_display = risco.get_perfil_exposicao_display()
                    if ' - ' in perfil_display:
                        perfil_display = perfil_display.split(' - ')[0]

                    # Método
                    metodo = risco.get_metodo_avaliacao_display()

                    # Classificação
                    classif = risco.get_classificacao_risco_display()

                    # Categoria do risco (FÍSICO, ACIDENTE, etc.)
                    categoria = risco.tipo_risco.get_categoria_display().upper()

                    # Agente com valor de medição se houver
                    agente_texto = risco.agente or '-'
                    avaliacao_quant = risco.avaliacoes_quantitativas.first()
                    if avaliacao_quant:
                        agente_texto = (
                            f"{risco.agente}<br/>"
                            f"{avaliacao_quant.resultado_medido} "
                            f"{avaliacao_quant.unidade_medida}"
                        )
                        # Adicionar referência da norma se houver
                        if avaliacao_quant.metodologia_utilizada:
                            agente_texto += f"<br/>{avaliacao_quant.metodologia_utilizada}"

                    # Efeitos à saúde + condição
                    efeitos_texto = risco.possiveis_efeitos_saude or '-'

                    dados_riscos.append([
                        Paragraph(categoria, style_td_center),
                        Paragraph(agente_texto, style_td),
                        Paragraph(risco.fonte_geradora or '-', style_td),
                        Paragraph(perfil_display, style_td_center),
                        Paragraph(risco.meio_propagacao or '-', style_td_center),
                        Paragraph(efeitos_texto, style_td),
                        Paragraph(str(risco.gravidade_g), style_td_center),
                        Paragraph(str(risco.exposicao_e), style_td_center),
                        Paragraph(str(risco.severidade_s), style_td_center),
                        Paragraph(str(risco.probabilidade_p), style_td_center),
                        Paragraph(classif, style_td_center),
                        Paragraph(metodo, style_td_center),
                        Paragraph(
                            risco.medidas_controle_existentes or '-',
                            style_td
                        ),
                    ])

                # Larguras proporcionais (total = largura_util)
                col_widths = [
                    largura_util * 0.06,   # RISCO
                    largura_util * 0.10,   # AGENTE
                    largura_util * 0.10,   # FONTE
                    largura_util * 0.07,   # PERFIL
                    largura_util * 0.06,   # MEIO
                    largura_util * 0.12,   # EFEITOS
                    largura_util * 0.05,   # GRAVIDADE
                    largura_util * 0.05,   # EXPOSIÇÃO
                    largura_util * 0.05,   # SEVERIDADE
                    largura_util * 0.06,   # PROBABILIDADE
                    largura_util * 0.08,   # CLASSIFICAÇÃO
                    largura_util * 0.07,   # MÉTODO
                    largura_util * 0.13,   # CONTROLE
                ]

                table_riscos = Table(
                    dados_riscos, colWidths=col_widths, repeatRows=1
                )
                table_riscos.setStyle(TableStyle([
                    # Header
                    ('BACKGROUND', (0, 0), (-1, 0), AZUL_ESCURO),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    # Corpo
                    ('FONTSIZE', (0, 0), (-1, -1), 6),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    # Grid
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#999999')),
                    # Zebra
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                     [colors.white, CINZA_ZEBRA]),
                    # Padding compacto
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('LEFTPADDING', (0, 0), (-1, -1), 2),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ]))

                story.append(table_riscos)
            else:
                story.append(Paragraph(
                    "<i>Nenhum risco identificado para este GES.</i>",
                    self.styles['Normal']
                ))

            # ═══════════════════════════════════════════════
            # AVALIAÇÕES QUANTITATIVAS (instrumentos)
            # ═══════════════════════════════════════════════

            avaliacoes = []
            for risco in riscos:
                for av in risco.avaliacoes_quantitativas.all():
                    avaliacoes.append(av)

            if avaliacoes:
                story.append(Spacer(1, 0.3 * cm))

                # Subtítulo
                story.append(Paragraph(
                    "AVALIAÇÕES QUANTITATIVAS",
                    subtitulo_style
                ))
                story.append(Spacer(1, 0.2 * cm))

                # Agrupar por tipo
                avaliacoes_por_tipo = {}
                for av in avaliacoes:
                    tipo = av.get_tipo_avaliacao_display().upper()
                    if tipo not in avaliacoes_por_tipo:
                        avaliacoes_por_tipo[tipo] = []
                    avaliacoes_por_tipo[tipo].append(av)

                # Para cada tipo, listar instrumentos (como no PDF modelo)
                style_instrumento_label = ParagraphStyle(
                    'InstrLabel',
                    parent=self.styles['Normal'],
                    fontSize=7,
                    fontName='Helvetica-Bold',
                    textColor=AZUL_ESCURO,
                )
                style_instrumento_valor = ParagraphStyle(
                    'InstrValor',
                    parent=self.styles['Normal'],
                    fontSize=7,
                    fontName='Helvetica',
                )

                instr_rows = []
                for tipo_nome, lista_av in avaliacoes_por_tipo.items():
                    # Cabeçalho do tipo
                    instr_rows.append([
                        Paragraph(f'<b>{tipo_nome}</b>', style_instrumento_label),
                        Paragraph('', style_instrumento_valor),
                    ])

                    # Instrumentos utilizados (sem duplicar)
                    instrumentos_vistos = set()
                    for av in lista_av:
                        equip = av.equipamento_utilizado or ''
                        if equip and equip not in instrumentos_vistos:
                            instrumentos_vistos.add(equip)
                            instr_rows.append([
                                Paragraph('Instrumentos utilizados:', style_instrumento_label),
                                Paragraph(f'➤ {equip}', style_instrumento_valor),
                            ])

                if instr_rows:
                    table_instr = Table(
                        instr_rows,
                        colWidths=[5 * cm, largura_util - 5 * cm]
                    )
                    table_instr.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 2),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                        ('LINEBELOW', (0, 0), (-1, -1), 0.25,
                         colors.Color(0.85, 0.85, 0.85)),
                    ]))
                    story.append(table_instr)

            # ── PageBreak entre GES ──
            story.append(PageBreak())

        return story

# ─────────────────────────────────────────────
  
#| Mudança | Antes | Agora |
#| --- | --- | --- |
#| Header da tabela | Fundo azul escuro, texto branco | Fundo cinza-azulado claro, texto preto ✅ |
#| Coluna 1 | "CARGO/FUNÇÃO" | "CARGOS" ✅ |
#| Coluna 2 | "QTD" (estreita) | "QUANT DE PROFISSIONAIS" (3.5cm) ✅ |
#| Marcação X | Verde com fundo verde claro | Preto sem fundo especial ✅ |
#| Células vazias | "–" cinza | Vazio ✅ |
#| Bordas | Cinza escuro, grid pesado | Cinza claro com borda azul externa ✅ |
#| Legenda | Header azul escuro | Mesmo estilo da tabela principal ✅ |
#| Texto introdutório | Parágrafo antes da tabela | Removido (como no modelo) ✅ |

    # ─────────────────────────────────────────────
    # 17. criar_matriz_treinamento
    # ─────────────────────────────────────────────
    def _criar_matriz_treinamento(self):
        """
        Cria a seção 17 - Matriz de Treinamento conforme PDF modelo oficial.
        Tabela cruzada: Cargos (linhas) × NRs/Treinamentos (colunas).
        Marca com 'X' onde o cargo necessita do treinamento.
        """
        from collections import OrderedDict

        story = []

        # Cores padrão
        AZUL_ESCURO = colors.HexColor('#003366')
        AZUL_HEADER = colors.HexColor('#4472C4')  # Azul médio do modelo
        CINZA_CLARO = colors.HexColor('#D9E2F3')  # Fundo header tabela
        CINZA_ZEBRA = colors.Color(0.95, 0.95, 0.95)

        story.append(Paragraph(
            "17. MATRIZ DE TREINAMENTO", self.styles['TituloSecao']
        ))
        story.append(Spacer(1, 0.3 * cm))

        # ─────────────────────────────────────────────
        # 1. COLETAR DADOS: cargo → set de treinamentos
        # ─────────────────────────────────────────────
        cargos_treinamentos = OrderedDict()
        todas_nrs = OrderedDict()

        grupos_ges = self.pgr.grupos_exposicao.filter(
            ativo=True
        ).select_related('cargo', 'funcao').order_by('codigo')

        for ges in grupos_ges:
            cargo_nome = None
            if ges.cargo:
                cargo_nome = ges.cargo.nome
            elif ges.funcao:
                cargo_nome = ges.funcao.nome

            if not cargo_nome:
                continue

            num_trab = ges.numero_trabalhadores or 0

            # Texto especial para visitantes/coordenadores
            texto_qtd = str(num_trab)
            if hasattr(ges, 'observacao_trabalhadores') and ges.observacao_trabalhadores:
                texto_qtd = ges.observacao_trabalhadores

            chave_cargo = cargo_nome
            if chave_cargo not in cargos_treinamentos:
                cargos_treinamentos[chave_cargo] = {
                    'num_trabalhadores': num_trab,
                    'texto_qtd': texto_qtd,
                    'nrs': set(),
                }
            else:
                cargos_treinamentos[chave_cargo]['num_trabalhadores'] += num_trab
                # Atualiza texto_qtd se for numérico
                if cargos_treinamentos[chave_cargo]['texto_qtd'].isdigit():
                    cargos_treinamentos[chave_cargo]['texto_qtd'] = str(
                        cargos_treinamentos[chave_cargo]['num_trabalhadores']
                    )

            # Percorrer riscos do GES → treinamentos necessários
            riscos = ges.riscos.prefetch_related(
                'treinamentos_necessarios__tipo_curso'
            ).all()

            for risco in riscos:
                for trein in risco.treinamentos_necessarios.select_related('tipo_curso').all():
                    tipo_curso = trein.tipo_curso
                    if not tipo_curso:
                        continue

                    nr_ref = tipo_curso.referencia_normativa or tipo_curso.nome
                    nr_ref = nr_ref.strip()

                    if nr_ref not in todas_nrs:
                        todas_nrs[nr_ref] = tipo_curso.nome

                    cargos_treinamentos[chave_cargo]['nrs'].add(nr_ref)

        # ─────────────────────────────────────────────
        # 2. VERIFICAR SE HÁ DADOS
        # ─────────────────────────────────────────────
        if not cargos_treinamentos or not todas_nrs:
            story.append(Paragraph(
                "A Matriz de Treinamento será gerada automaticamente quando os "
                "treinamentos necessários forem vinculados aos riscos identificados "
                "nos Grupos de Exposição Similar (GES).",
                self.styles['Justificado']
            ))
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(
                "<i>Para preencher esta seção, cadastre os treinamentos necessários "
                "(tipo de curso com referência normativa) nos riscos de cada GES.</i>",
                self.styles['Normal']
            ))
            story.append(PageBreak())
            return story

        # ─────────────────────────────────────────────
        # 4. MONTAR A TABELA CRUZADA
        # ─────────────────────────────────────────────
        lista_nrs = list(todas_nrs.keys())
        num_nrs = len(lista_nrs)

        # ── Estilos das células ──
        style_header = ParagraphStyle(
            'MatrizHeader',
            parent=self.styles['Normal'],
            fontSize=7,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            alignment=TA_CENTER,
            leading=9,
        )
        style_cargo = ParagraphStyle(
            'MatrizCargo',
            parent=self.styles['Normal'],
            fontSize=7.5,
            fontName='Helvetica',
            leading=9,
        )
        style_qtd = ParagraphStyle(
            'MatrizQtd',
            parent=self.styles['Normal'],
            fontSize=7.5,
            fontName='Helvetica',
            alignment=TA_CENTER,
            leading=9,
        )
        style_x = ParagraphStyle(
            'MatrizX',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            alignment=TA_CENTER,
            leading=10,
        )
        style_vazio = ParagraphStyle(
            'MatrizVazio',
            parent=self.styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER,
            leading=9,
        )

        # ── Larguras das colunas ──
        largura_util = A4[0] - 3 * cm  # ~15.1 cm
        col_cargo = 3.5 * cm
        col_qtd = 3.5 * cm
        espaco_restante = largura_util - col_cargo - col_qtd
        col_nr = espaco_restante / max(num_nrs, 1)
        col_nr = max(col_nr, 1.2 * cm)
        col_nr = min(col_nr, 2.5 * cm)

        col_widths = [col_cargo, col_qtd] + [col_nr] * num_nrs

        # ── Header ──
        header_row = [
            Paragraph('<b>CARGOS</b>', style_header),
            Paragraph('<b>QUANT DE<br/>PROFISSIONAIS</b>', style_header),
        ]
        for nr_ref in lista_nrs:
            header_row.append(Paragraph(f'<b>{nr_ref}</b>', style_header))

        dados_tabela = [header_row]

        # ── Linhas de dados ──
        for cargo_nome, info in cargos_treinamentos.items():
            row = [
                Paragraph(cargo_nome, style_cargo),
                Paragraph(info['texto_qtd'], style_qtd),
            ]
            for nr_ref in lista_nrs:
                if nr_ref in info['nrs']:
                    row.append(Paragraph('<b>X</b>', style_x))
                else:
                    row.append(Paragraph('', style_vazio))
            dados_tabela.append(row)

        # ── Construir tabela ──
        table_matriz = Table(dados_tabela, colWidths=col_widths, repeatRows=1)

        estilo_tabela = [
            # Header - fundo cinza azulado claro como no modelo
            ('BACKGROUND', (0, 0), (-1, 0), CINZA_CLARO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            # Alinhamento
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Bordas - linhas finas cinza como no modelo
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BFBFBF')),
            # Borda externa mais grossa
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#8DB4E2')),
            # Linha abaixo do header mais grossa
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#8DB4E2')),
            # Zebra suave
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#F2F2F2')]),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]

        table_matriz.setStyle(TableStyle(estilo_tabela))
        story.append(table_matriz)
        story.append(Spacer(1, 0.5 * cm))

        # ─────────────────────────────────────────────
        # 5. LEGENDA DOS TREINAMENTOS
        # ─────────────────────────────────────────────
        story.append(Paragraph(
            "<b>LEGENDA DOS TREINAMENTOS</b>",
            ParagraphStyle(
                'LegendaTitulo',
                parent=self.styles['Normal'],
                fontSize=8,
                fontName='Helvetica-Bold',
                spaceAfter=6,
            )
        ))

        style_legenda_ref = ParagraphStyle(
            'LegendaRef',
            parent=self.styles['Normal'],
            fontSize=7.5,
            fontName='Helvetica-Bold',
            leading=9,
            alignment=TA_CENTER,
        )
        style_legenda_nome = ParagraphStyle(
            'LegendaNome',
            parent=self.styles['Normal'],
            fontSize=7.5,
            fontName='Helvetica',
            leading=9,
        )

        legenda_rows = [
            [
                Paragraph('<b>REFERÊNCIA</b>', style_header),
                Paragraph('<b>TREINAMENTO</b>', style_header),
            ]
        ]
        for nr_ref, nome_curso in todas_nrs.items():
            legenda_rows.append([
                Paragraph(f'<b>{nr_ref}</b>', style_legenda_ref),
                Paragraph(nome_curso, style_legenda_nome),
            ])

        col_legenda_ref = 3 * cm
        col_legenda_nome = largura_util - col_legenda_ref

        table_legenda = Table(
            legenda_rows,
            colWidths=[col_legenda_ref, col_legenda_nome],
            repeatRows=1
        )
        table_legenda.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), CINZA_CLARO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BFBFBF')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#8DB4E2')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#8DB4E2')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#F2F2F2')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(table_legenda)

        story.append(PageBreak())
        return story



    # =================================================================
    # ASSINATURAS
    # =================================================================

    def _criar_pagina_assinaturas(self):
        """Cria a página de assinaturas"""
        story = []
        story.append(Paragraph(
                "ENCERRAMENTO\n\n",
                self.styles['Justificado']
            ))
        story.append(Paragraph(
                "Este Programa de Gerenciamento de Riscos foi elaborado por "
                "{empres} através de seus representantes em 14 de Outubro de 2025.\n",
                self.styles['Justificado']
            ))
        story.append(Paragraph("ASSINATURAS", self.styles['TituloSecao']))
        story.append(Spacer(1, 1 * cm))

        responsavel_info_qs = self.pgr.responsavel_info.select_related(
            'profissional'
        ).all()

        if responsavel_info_qs.exists():
            for resp_info in responsavel_info_qs:
                prof = resp_info.profissional
                if prof:
                    story.append(Spacer(1, 1.5 * cm))
                    story.append(Paragraph(
                        "_" * 60, self.styles['Normal']
                    ))
                    story.append(Paragraph(
                        f"<b>{prof.nome_completo}</b>",
                        self.styles['Normal']
                    ))
                    story.append(Paragraph(
                        f"{prof.funcao or ''}", self.styles['Normal']
                    ))
                    registro = ''
                    if prof.registro_classe:
                        orgao = prof.orgao_classe or ''
                        registro = f"{orgao} {prof.registro_classe}".strip()
                    if registro:
                        story.append(Paragraph(
                            registro, self.styles['Normal']
                        ))
                    story.append(Spacer(1, 0.5 * cm))
        else:
            story.append(Paragraph(
                "<i>Nenhum responsável vinculado a este documento.</i>",
                self.styles['Normal']
            ))

        return story
    
    def _criar_pagina_anexos(self):
        """
        Cria a seção de ANEXOS no final do PDF.
        Lista todos os anexos vinculados ao PGR com seus títulos.
        """
        from pgr_gestao.models import AnexoPGR

        anexos = AnexoPGR.objects.filter(
            pgr_documento=self.pgr,
            incluir_no_pdf=True
        ).order_by('ordem', 'numero_romano')

        if not anexos.exists():
            return []

        story = []
        story.append(PageBreak())
        story.append(Paragraph("ANEXOS", self.styles['TituloSecao']))
        story.append(Spacer(1, 0.5 * cm))

        story.append(Paragraph(
            "Os seguintes documentos complementares fazem parte integrante deste PGR:",
            self.styles['Justificado']
        ))
        story.append(Spacer(1, 0.3 * cm))

        # Tabela com lista dos anexos
        dados = [['Nº', 'TÍTULO', 'TIPO', 'ARQUIVO']]

        for anexo in anexos:
            dados.append([
                f"ANEXO {anexo.numero_romano}",
                anexo.titulo,
                anexo.get_tipo_anexo_display(),
                anexo.nome_arquivo_original or '—'
            ])

        col_widths = [2.5 * cm, 7 * cm, 4.5 * cm, 4 * cm]
        story.extend(self._criar_tabela_padrao(dados, col_widths))

        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(
            "<i>Nota: Os anexos originais encontram-se disponíveis em formato digital "
            "no sistema de gestão SST e podem ser acessados através do módulo PGR.</i>",
            self.styles['Normal']
        ))

        return story


    # =================================================================
    # GERAÇÃO DO PDF COMPLETO
    # =================================================================

    def gerar_pdf(self):
        """Gera o PDF completo do PGR"""
        buffer = BytesIO()
        width, height = A4

        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2 * cm,
        )

        frame_capa = Frame(
            2.5 * cm, 2 * cm, width - 4 * cm, height - 5 * cm,
            id='frame_capa'
        )
        frame_normal = Frame(
            1.5 * cm, 2 * cm, width - 3 * cm, height - 4.5 * cm,
            id='frame_normal'
        )

        template_capa = PageTemplate(
            id='capa', frames=[frame_capa], onPage=draw_capa_background,
        )
        template_normal = PageTemplate(
            id='normal', frames=[frame_normal], onPage=draw_header_footer,
        )
        doc.addPageTemplates([template_capa, template_normal])

        story = []

        # CAPA
        story.extend(self._criar_capa())

        # SEÇÕES 1-8 (textos)
        story.extend(self._criar_caracterizacao_empresa())
        story.extend(self._criar_controle_revisao())
        story.extend(self._criar_documento_base())
        story.extend(self._criar_definicoes())
        story.extend(self._criar_estrutura_pgr())
        story.extend(self._criar_responsabilidades())
        story.extend(self._criar_diretrizes())
        story.extend(self._criar_desenvolvimento())
        story.extend(self._criar_metodologia())
        # SEÇÃO 9 — Tabelas de Classificação (Tabelas 1-8 visuais)
        story.extend(self._criar_tabelas_classificacao())
        # SEÇÃO 10-15 (textos + cronograma)
        story.extend(self._criar_plano_acao_texto())
        story.extend(self._criar_medidas_protecao())
        story.extend(self._criar_cronograma_acoes())
        story.extend(self._criar_divulgacao())
        story.extend(self._criar_recomendacoes())
        story.extend(self._criar_legislacao())
        # SEÇÃO 16 — Levantamento dos Riscos (inventário por GES)
        story.extend(self._criar_inventario_riscos())
        # SEÇÃO 17 — Matriz de Treinamento
        story.extend(self._criar_matriz_treinamento())
        # ASSINATURAS
        story.extend(self._criar_pagina_assinaturas())
        # ANEXOS
        story.extend(self._criar_pagina_anexos())

        doc.build(story)
        buffer.seek(0)
        return buffer


# =================================================================
# HELPER: Tabela padrão com estilo PGR

#| Tabela | Visual |
#| --- | --- |
#| Tabela 1 (Probabilidade) | 4 colunas: Nível, Classificação, Descrição, Frequência — header azul, zebra cinza |
#| Tabela 2 (Gravidade) | 3 colunas: Nível, Classificação, Descrição — header azul, zebra cinza |
#| Tabela 3 (Exposição) | 3 colunas: Nível, Classificação, Descrição — header azul, zebra cinza |
#| Tabela 4 (Matriz G×E) | Matriz 5×5 colorida: 🟢A 🟡B 🟠C 🔴D 🔴E |
#| Tabela 5 (Severidade) | Cores graduadas do verde ao vermelho |
#| Tabela 6 (Mitigação) | 5 colunas com priorização 1°→5° |
#| Tabela 7 (Priorização) | 4 linhas coloridas: verde→amarelo→laranja→vermelho |
#| Tabela 8 (Matriz S×P) | Matriz 5×5 colorida: 🟢B 🟡T 🟠M 🔴S |
            
# =================================================================

    def _criar_tabela_padrao(self, dados, col_widths, titulo=None, subtitulo=None):
        """
        Cria uma tabela com o estilo padrão do PGR:
        - Header azul escuro com texto branco
        - Zebra stripes cinza claro
        - Grid cinza
        - Título opcional acima
        """
        story = []

        if titulo:
            story.append(Paragraph(
                f"<b>{titulo}</b>", self.styles['TituloSecao']
            ))
        if subtitulo:
            story.extend(self._texto_para_paragrafos(subtitulo))
            story.append(Spacer(1, 0.2 * cm))

        table = Table(dados, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            # Alinhamento
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Zebra
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        story.append(table)
        story.append(Spacer(1, 0.4 * cm))
        return story

    def _criar_matriz_colorida(self, dados, col_widths, cores_celulas, titulo=None, subtitulo=None):
        """
        Cria uma matriz (tabela) com cores condicionais nas células.
        cores_celulas = dict de {(row, col): HexColor}
        """
        story = []

        if titulo:
            story.append(Paragraph(
                f"<b>{titulo}</b>", self.styles['TituloSecao']
            ))
        if subtitulo:
            story.extend(self._texto_para_paragrafos(subtitulo))
            story.append(Spacer(1, 0.2 * cm))

        table = Table(dados, colWidths=col_widths)

        # Estilo base
        estilo_base = [
            # Header linha 0
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            # Header coluna 0
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#003366')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]

        # Cores condicionais das células
        for (row, col), cor in cores_celulas.items():
            estilo_base.append(('BACKGROUND', (col, row), (col, row), cor))
            # Texto branco para cores escuras
            if cor in [
                colors.HexColor('#dc3545'), colors.HexColor('#c0392b'),
                colors.HexColor('#6f0000'), colors.HexColor('#003366'),
            ]:
                estilo_base.append(
                    ('TEXTCOLOR', (col, row), (col, row), colors.white)
                )

        table.setStyle(TableStyle(estilo_base))
        story.append(table)
        story.append(Spacer(1, 0.4 * cm))
        return story

    # =================================================================
    # 9. TABELAS DE CLASSIFICAÇÃO (Tabelas 1 a 8)
    # =================================================================

    def _criar_tabelas_classificacao(self):
        """
        Cria a seção 9 completa:
        - Tabela de Grupos de Riscos (I a V) com cores
        - Tabelas 1-8 de classificação
        Conforme PDF modelo oficial (páginas 15-22).
        """
        nome_empresa = self._get_nome_empresa()
        story = []

        ts = self.styles['TabelaTitulo']
        tc = self.styles['TabelaTextoCentro']
        tt = self.styles['TabelaTexto']

        # ═══════════════════════════════════════════════
        # TÍTULO DA SEÇÃO 9
        # ═══════════════════════════════════════════════
        story.append(Paragraph(
            "9. INVENTÁRIO DE RISCOS, PERIGOS, ASPECTOS E IMPACTOS",
            self.styles['TituloSecao']
        ))
        story.append(Paragraph(
            "RISCOS AMBIENTAIS E OCUPACIONAIS",
            self.styles['SubtituloCapa']
        ))
        story.append(Spacer(1, 0.5 * cm))

        # ═══════════════════════════════════════════════
        # TABELA DE GRUPOS DE RISCOS (I a V)
        # ═══════════════════════════════════════════════
        # Cores oficiais por grupo
        COR_FISICO = colors.HexColor('#28a745')       # Verde
        COR_QUIMICO = colors.HexColor('#dc3545')      # Vermelho
        COR_BIOLOGICO = colors.HexColor('#6f4e37')     # Marrom
        COR_ERGONOMICO = colors.HexColor('#ffc107')    # Amarelo
        COR_ACIDENTE = colors.HexColor('#0d6efd')      # Azul

        # Estilos para header dos grupos
        estilo_grupo_header = ParagraphStyle(
            'GrupoHeader',
            parent=self.styles['Normal'],
            fontSize=7,
            fontName='Helvetica-Bold',
            textColor=colors.white,
            alignment=TA_CENTER,
            leading=9,
        )
        estilo_grupo_header_escuro = ParagraphStyle(
            'GrupoHeaderEscuro',
            parent=self.styles['Normal'],
            fontSize=7,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            alignment=TA_CENTER,
            leading=9,
        )
        estilo_grupo_celula = ParagraphStyle(
            'GrupoCelula',
            parent=self.styles['Normal'],
            fontSize=6.5,
            alignment=TA_CENTER,
            leading=8,
        )

        # ── Header principal ──
        header_grupos = [
            '',
            Paragraph('<b>GRUPO I</b>', estilo_grupo_header),
            Paragraph('<b>GRUPO II</b>', estilo_grupo_header),
            Paragraph('<b>GRUPO III</b>', estilo_grupo_header),
            Paragraph('<b>GRUPO IV</b>', estilo_grupo_header_escuro),
            Paragraph('<b>GRUPO V</b>', estilo_grupo_header),
        ]

        # ── Sub-header (tipo de risco) ──
        sub_header = [
            '',
            Paragraph('<b>RISCOS FÍSICOS</b>', estilo_grupo_header),
            Paragraph('<b>RISCOS QUÍMICOS</b>', estilo_grupo_header),
            Paragraph('<b>RISCOS BIOLÓGICOS</b>', estilo_grupo_header),
            Paragraph('<b>RISCOS ERGONÔMICOS</b>', estilo_grupo_header_escuro),
            Paragraph('<b>RISCOS DE ACIDENTE</b>', estilo_grupo_header),
        ]

        # ── Dados dos grupos ──
        gc = estilo_grupo_celula
        dados_grupos = [
            header_grupos,
            sub_header,
            [
                '', Paragraph('RUÍDOS', gc), Paragraph('POEIRAS', gc),
                Paragraph('VÍRUS', gc), Paragraph('ESFORÇO FÍSICO<br/>INTENSO', gc),
                Paragraph('ARRANJO FÍSICO<br/>INADEQUADO', gc),
            ],
            [
                '', Paragraph('VIBRAÇÕES', gc), Paragraph('FUMOS<br/>METÁLICOS', gc),
                Paragraph('BACTÉRIAS', gc),
                Paragraph('LEVANTAMENTO<br/>E TRANSPORTE<br/>MANUAL DE PESO', gc),
                Paragraph('MÁQUINAS E<br/>EQUIPAMENTOS<br/>SEM PROTEÇÃO', gc),
            ],
            [
                '', Paragraph('RADIAÇÃO<br/>IONIZANTE', gc), Paragraph('NÉVOAS', gc),
                Paragraph('PROTOZOÁRIOS', gc),
                Paragraph('EXIGÊNCIA DE<br/>POSTURA<br/>INADEQUADA', gc),
                Paragraph('FERRAMENTAS<br/>INADEQUADAS OU<br/>DEFEITUOSAS', gc),
            ],
            [
                '', Paragraph('FRIO', gc), Paragraph('NEBLINAS', gc),
                Paragraph('FUNGOS', gc),
                Paragraph('CONTROLE RÍGIDO<br/>DE<br/>PRODUTIVIDADE', gc),
                Paragraph('ELETRICIDADE', gc),
            ],
            [
                '', Paragraph('CALOR', gc), Paragraph('GASES', gc),
                Paragraph('PARASITAS', gc),
                Paragraph('IMPOSIÇÃO DE<br/>RITMOS<br/>EXCESSIVOS', gc),
                Paragraph('PROBABILIDADE<br/>DE INCÊNDIO<br/>EXPLOSÃO', gc),
            ],
            [
                '', Paragraph('PRESSÕES<br/>ANORMAIS', gc), Paragraph('VAPORES', gc),
                Paragraph('BACILOS', gc),
                Paragraph('TRABALHO EM<br/>TURNO E<br/>NOTURNO', gc),
                Paragraph('ARMAZENAMENTO<br/>INADEQUADO', gc),
            ],
            [
                '', Paragraph('UMIDADE', gc),
                Paragraph('SUBSTÂNCIAS,<br/>COMPOSTOS<br/>QUÍMICOS EM<br/>GERAL', gc),
                Paragraph('INSETOS<br/>COBRAS,<br/>ARANHAS<br/>ETC.', gc),
                Paragraph('JORNADA DE<br/>TRABALHO<br/>PROLONGADA', gc),
                Paragraph('ANIMAIS<br/>PEÇONHENTOS', gc),
            ],
            [
                '', Paragraph('TEMPERATURAS<br/>EXTREMAS', gc), '', '',
                Paragraph('MONOTONIA E<br/>REPETITIVIDADE', gc),
                Paragraph('ILUMINAÇÃO<br/>INADEQUADA', gc),
            ],
            [
                '', '', '', '',
                Paragraph('OUTRAS<br/>SITUAÇÕES<br/>CAUSADORAS DE<br/>STRESS<br/>'
                          'FÍSICO/OU<br/>PSÍQUICO', gc),
                Paragraph('OUTRAS<br/>SITUAÇÕES DE<br/>RISCO QUE<br/>PODERÃO<br/>'
                          'CONTRIBUIR PARA<br/>A OCORRÊNCIA DE<br/>ACIDENTES', gc),
            ],
        ]

        col_w = 3.0 * cm
        col_widths_grupos = [0.5 * cm, col_w, col_w, col_w, col_w, col_w]

        table_grupos = Table(dados_grupos, colWidths=col_widths_grupos)
        table_grupos.setStyle(TableStyle([
            # ── Grid ──
            ('GRID', (1, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),

            # ── Header principal (linha 0) — cores por grupo ──
            ('BACKGROUND', (1, 0), (1, 0), COR_FISICO),
            ('BACKGROUND', (2, 0), (2, 0), COR_QUIMICO),
            ('BACKGROUND', (3, 0), (3, 0), COR_BIOLOGICO),
            ('BACKGROUND', (4, 0), (4, 0), COR_ERGONOMICO),
            ('BACKGROUND', (5, 0), (5, 0), COR_ACIDENTE),

            # ── Sub-header (linha 1) — mesmas cores ──
            ('BACKGROUND', (1, 1), (1, 1), COR_FISICO),
            ('BACKGROUND', (2, 1), (2, 1), COR_QUIMICO),
            ('BACKGROUND', (3, 1), (3, 1), COR_BIOLOGICO),
            ('BACKGROUND', (4, 1), (4, 1), COR_ERGONOMICO),
            ('BACKGROUND', (5, 1), (5, 1), COR_ACIDENTE),

            # ── Corpo — fundo branco ──
            ('BACKGROUND', (1, 2), (-1, -1), colors.white),

            # ── Texto branco nos headers (exceto amarelo) ──
            ('TEXTCOLOR', (1, 0), (1, 1), colors.white),
            ('TEXTCOLOR', (2, 0), (2, 1), colors.white),
            ('TEXTCOLOR', (3, 0), (3, 1), colors.white),
            ('TEXTCOLOR', (4, 0), (4, 1), colors.black),  # Amarelo = texto preto
            ('TEXTCOLOR', (5, 0), (5, 1), colors.white),

            # ── Coluna 0 invisível ──
            ('BACKGROUND', (0, 0), (0, -1), colors.white),
            ('LINEWIDTH', (0, 0), (0, -1), 0),

            # ── Padding ──
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),

            # ── Font sizes ──
            ('FONTSIZE', (0, 0), (-1, -1), 7),
        ]))

        story.append(table_grupos)
        story.append(Spacer(1, 0.5 * cm))

        # ─────────────────────────────────────────────
        # TEXTO INTRODUTÓRIO
        # ─────────────────────────────────────────────
        texto_intro = get_texto_secao(
            self.pgr, 'inventario_riscos_intro', nome_empresa
        )
        if texto_intro:
            story.extend(self._texto_para_paragrafos(texto_intro))
            story.append(Spacer(1, 0.3 * cm))
        else:
            story.append(Paragraph(
                "Durante as avaliações serão considerados os seguintes aspectos:",
                self.styles['Justificado']
            ))
            story.append(Spacer(1, 0.3 * cm))

        # Texto sobre Probabilidade do Risco
        story.append(Paragraph(
            "<b>PROBABILIDADE DO RISCO</b>", self.styles['Normal']
        ))
        story.append(Paragraph(
            "A gradação da probabilidade da ocorrência do dano (efeito crítico) "
            "é feita atribuindo-se um índice de probabilidade (P) variando de 1 a 5.",
            self.styles['Justificado']
        ))
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph(
            "Os métodos utilizados para atribuir valor à probabilidade foram:",
            self.styles['Justificado']
        ))
        story.extend(self._texto_para_paragrafos(
            "- Definido com base em dados estatísticos de acidentes ou doenças "
            "relacionadas ao trabalho obtidos ou fornecidos pela empresa ou do setor "
            "de atividade quando predominam situações similares;\n"
            "- Definido a partir do perfil de exposição qualitativo, quando não forem "
            "possíveis ou disponíveis dados quantitativos;\n"
            "- Quanto maior intensidade, duração e frequência da exposição maior será "
            "a probabilidade de ocorrência do dano e maior será o valor atribuído a P."
        ))
        story.append(PageBreak())

        # ═══════════════════════════════════════════════
        # TABELA 1 — PROBABILIDADE (P)
        # ═══════════════════════════════════════════════
        dados_t1 = [
            [
                Paragraph('<b>NÍVEL</b>', ts),
                Paragraph('<b>CLASSIFICAÇÃO</b>', ts),
                Paragraph('<b>DESCRIÇÃO</b>', ts),
                Paragraph('<b>FREQUÊNCIA</b>', ts),
            ],
            [
                Paragraph('1', tc), Paragraph('IMPROVÁVEL', tc),
                Paragraph('Probabilidade de 1 ocorrência até uma vez em cada 50 anos', tt),
                Paragraph('(P ≤ 1 ocorrência/50 anos)', tt),
            ],
            [
                Paragraph('2', tc), Paragraph('REMOTO', tc),
                Paragraph('Probabilidade de 1 ocorrência em cada 5 anos', tt),
                Paragraph('(1 oc./50 anos &lt; P ≤ 1 oc./5 anos)', tt),
            ],
            [
                Paragraph('3', tc), Paragraph('OCASIONAL', tc),
                Paragraph('Probabilidade de 1 ocorrência em cada ano', tt),
                Paragraph('(1 oc./5 anos &lt; P ≤ 1 oc./ano)', tt),
            ],
            [
                Paragraph('4', tc), Paragraph('PROVÁVEL', tc),
                Paragraph('Probabilidade de 1 ocorrência em cada mês', tt),
                Paragraph('(1 oc./ano &lt; P ≤ 1 oc./mês)', tt),
            ],
            [
                Paragraph('5', tc), Paragraph('FREQUENTE', tc),
                Paragraph('Probabilidade de ocorrência mais do que uma vez por mês', tt),
                Paragraph('(P &gt; 1 ocorrência/mês)', tt),
            ],
        ]
        story.extend(self._criar_tabela_padrao(
            dados_t1,
            col_widths=[1.2*cm, 2.8*cm, 6.5*cm, 5.5*cm],
            titulo='TABELA 1',
            subtitulo='CRITÉRIOS PARA GRADAÇÃO DA PROBABILIDADE DE OCORRÊNCIA DO DANO (P)\n\n'))
                
        story.append(Paragraph(
                "Conceito que caracteriza a chance de que o perigo se concretize, ou seja, "
                "a probabilidade de consequência prejudicial ao ser humano ou a empresa, caso "
                "permita-se que as condições inseguras persistam.\n",
            self.styles['Justificado']       
        ))
        # Observação
        story.append(Paragraph("<b>OBSERVAÇÃO</b>", self.styles['Normal']))
        story.append(Paragraph(
            "Se a exposição a contaminantes atmosféricos ou ao ruído for avaliada como "
            "excessiva, ou seja, maior que o limite de exposição permitido, ou acima do "
            "nível de ação, deve-se definir o índice de probabilidade de ocorrência do "
            "dano estimado como 1, 2, 3, 4 ou 5 por julgamento profissional do avaliador, "
            "conforme o grau de adequação do EPI ao tipo de exposição, sua manutenção e "
            "uso efetivo.",
            self.styles['Justificado']
        ))
        story.append(PageBreak())

        # ═══════════════════════════════════════════════
        # TABELA 2 — GRAVIDADE (G)
        # ═══════════════════════════════════════════════
        dados_t2 = [
            [
                Paragraph('<b>NÍVEL</b>', ts),
                Paragraph('<b>CLASSIFICAÇÃO</b>', ts),
                Paragraph('<b>DESCRIÇÃO</b>', ts),
            ],
            [
                Paragraph('1', tc), Paragraph('NEGLIGENCIÁVEL', tc),
                Paragraph('Danos pessoais ligeiros ou sem danos, mal-estar passageiro, '
                            'pequenas lesões sem qualquer tipo de incapacidade. (Sem baixa)', tt),
            ],
            [
                Paragraph('2', tc), Paragraph('MARGINAL', tc),
                Paragraph('Danos ou doenças ocupacionais menores com ou sem incapacidade temporária '
                            'sem assistência médica especializada, primeiro socorro. '
                            '(Lesões ou doenças até 10 dias de baixa)', tt),
            ],
            [
                Paragraph('3', tc), Paragraph('MODERADO', tc),
                Paragraph('Danos ou doenças ocupacionais de média gravidade, requerendo assistência '
                            'médica e baixa com duração superior a 10 dias. '
                            '(Lesões ou doenças suscetíveis de provocar baixa entre 11 e 60 dias)', tt),
            ],
            [
                Paragraph('4', tc), Paragraph('GRAVE', tc),
                Paragraph('Danos ou doenças ocupacionais graves, lesões com incapacidade temporária '
                            'ou parcial permanente, internamento hospitalar. '
                            '(Incapacidade parcial permanente, ou baixa superior a 60 dias)', tt),
            ],
            [
                Paragraph('5', tc), Paragraph('CRÍTICO', tc),
                Paragraph('Morte ou incapacidade total permanente', tt),
            ],
        ]
        story.extend(self._criar_tabela_padrao(
            dados_t2,
            col_widths=[1.2*cm, 3*cm, 11.8*cm],
            titulo='TABELA 2',
            subtitulo='CRITÉRIOS PARA GRADAÇÃO DA GRAVIDADE DO DANO (G)\n\n'))
                      
        story.append(Paragraph(
                    "Para a gradação da gravidade do dano potencial (efeito crítico) "
                    "atribui-se um índice de gravidade (G) variando de 1 a 5 conforme "
                    "os critérios especiais da tabela abaixo.\n",
            self.styles['Justificado']
        ))
        story.append(PageBreak())

        # ═══════════════════════════════════════════════
        # TABELA 3 — EXPOSIÇÃO (E)
        # ═══════════════════════════════════════════════
        dados_t3 = [
            [
                Paragraph('<b>NÍVEL</b>', ts),
                Paragraph('<b>CLASSIFICAÇÃO</b>', ts),
                Paragraph('<b>DESCRIÇÃO</b>', ts),
            ],
            [
                Paragraph('1', tc), Paragraph('ESPORÁDICA', tc),
                Paragraph('Exposição acontece pelo menos uma vez por ano por um '
                            'período curto de tempo ou nunca acontece', tt),
            ],
            [
                Paragraph('2', tc), Paragraph('POUCO FREQUENTE', tc),
                Paragraph('Exposição acontece algumas vezes por mês', tt),
            ],
            [
                Paragraph('3', tc), Paragraph('OCASIONAL', tc),
                Paragraph('Exposição acontece várias vezes por semana ou várias vezes '
                            'por dia por períodos curtos (&lt; 60 min.)', tt),
            ],
            [
                Paragraph('4', tc), Paragraph('FREQUENTE', tc),
                Paragraph('Exposição ocorre várias vezes por dia por períodos não '
                            'prolongados (&lt; 120 min. seguidos)', tt),
            ],
            [
                Paragraph('5', tc), Paragraph('CONTÍNUA', tc),
                Paragraph('Exposição por períodos diários ou várias vezes por dia '
                            'por períodos prolongados (&gt; 120 min. seguidos)', tt),
            ],
        ]
        story.extend(self._criar_tabela_padrao(
            dados_t3,
            col_widths=[1.2*cm, 3.5*cm, 11.3*cm],
            titulo='TABELA 3',
            subtitulo='MONITORAMENTO DA EXPOSIÇÃO (GRAU DE EXPOSIÇÃO AO RISCO)\n\n'))
            
        story.append(Paragraph(
                    "Para a gradação da exposição ao dano potencial (efeito crítico) atribui-se um "
                    "índice de exposição (E) variando de 1 a 5 conforme os critérios especiais da Tabela 3.\n",
            self.styles['Justificado']
        ))
        story.append(PageBreak())

        # ═══════════════════════════════════════════════
        # TABELA 4 — MATRIZ SEVERIDADE (G x E)
        # ═══════════════════════════════════════════════
        # Cores por nível de severidade
        COR_A = colors.HexColor('#28a745')  # Verde
        COR_B = colors.HexColor('#ffc107')  # Amarelo
        COR_C = colors.HexColor('#fd7e14')  # Laranja
        COR_D = colors.HexColor('#dc3545')  # Vermelho
        COR_E = colors.HexColor('#6f0000')  # Vermelho escuro

        dados_t4 = [
            ['', Paragraph('<b>G=1</b>', ts), Paragraph('<b>G=2</b>', ts),
                Paragraph('<b>G=3</b>', ts), Paragraph('<b>G=4</b>', ts),
                Paragraph('<b>G=5</b>', ts)],
            [Paragraph('<b>E=1</b>', ts), 'A', 'A', 'A', 'B', 'B'],
            [Paragraph('<b>E=2</b>', ts), 'A', 'B', 'B', 'C', 'D'],
            [Paragraph('<b>E=3</b>', ts), 'A', 'B', 'C', 'D', 'D'],
            [Paragraph('<b>E=4</b>', ts), 'B', 'C', 'D', 'E', 'E'],
            [Paragraph('<b>E=5</b>', ts), 'B', 'D', 'D', 'E', 'E'],
        ]

        # Mapa de cores
        MAPA_COR = {'A': COR_A, 'B': COR_B, 'C': COR_C, 'D': COR_D, 'E': COR_E}
        cores_t4 = {}
        matriz_valores = [
            ['A', 'A', 'A', 'B', 'B'],
            ['A', 'B', 'B', 'C', 'D'],
            ['A', 'B', 'C', 'D', 'D'],
            ['B', 'C', 'D', 'E', 'E'],
            ['B', 'D', 'D', 'E', 'E'],
        ]
        for r_idx, row in enumerate(matriz_valores):
            for c_idx, val in enumerate(row):
                cores_t4[(r_idx + 1, c_idx + 1)] = MAPA_COR[val]

        story.extend(self._criar_matriz_colorida(
            dados_t4,
            col_widths=[2*cm, 2.4*cm, 2.4*cm, 2.4*cm, 2.4*cm, 2.4*cm],
            cores_celulas=cores_t4,
            titulo='TABELA 4',
            subtitulo='MATRIZ DE RISCO PARA ESTIMAR A SEVERIDADE DO RISCO (AVALIAÇÃO DE RISCO)\n\n'))
                        
        story.append(Paragraph(
                    "Estimar e definir a categoria de cada risco, a partir da combinação dos valores "
                    "atribuídos para exposição (E) e gravidade (G) do dano, utilizando a matriz "
                    "apresentada na Tabela 4, que define a categoria de risco resultante dessa combinação.\n",
            self.styles['Justificado']
        ))

        # ═══════════════════════════════════════════════
        # TABELA 5 — SEVERIDADE (S)
        # ═══════════════════════════════════════════════
        dados_t5 = [
            [Paragraph('<b>NÍVEL</b>', ts), Paragraph('<b>CLASSIFICAÇÃO</b>', ts)],
            [Paragraph('A', tc), Paragraph('NEGLIGENCIÁVEL', tc)],
            [Paragraph('B', tc), Paragraph('MARGINAL', tc)],
            [Paragraph('C', tc), Paragraph('GRAVE', tc)],
            [Paragraph('D', tc), Paragraph('MUITO GRAVE', tc)],
            [Paragraph('E', tc), Paragraph('CRÍTICO', tc)],
        ]

        # Cores por linha
        story.append(Paragraph(
            "<b>TABELA 5</b>", self.styles['TituloSecao']
        ))
        story.append(Paragraph(
            "CRITÉRIOS PARA GRADAÇÃO DA SEVERIDADE DO DANO SE OCORRER (S)",
            self.styles['Justificado']
        ))
        story.append(Spacer(1, 0.2 * cm))

        table_t5 = Table(dados_t5, colWidths=[3*cm, 8*cm])
        table_t5.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Cores por severidade
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#005514")),  # A Verde escuro
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor("#00ff3c")),  # B Verede claro
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#fff200")),  # C lAmarelo
            ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor("#ff9900")),  # D Laranja
            ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor("#ff0000")),  # E vermelho
            ('TEXTCOLOR', (0, 5), (-1, 5), colors.white),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table_t5)
        story.append(PageBreak())

        # ═══════════════════════════════════════════════
        # TABELA 6 — AÇÕES DE MITIGAÇÃO
        # ═══════════════════════════════════════════════
        dados_t6 = [
            [
                Paragraph('<b>PRIORIZAÇÃO<br/>DAS AÇÕES</b>', ts),
                Paragraph('<b>MEDIDA DE<br/>PREVENÇÃO</b>', ts),
                Paragraph('<b>SIGNIFICADO</b>', ts),
                Paragraph('<b>DESCRIÇÃO</b>', ts),
                Paragraph('<b>REDUÇÃO<br/>DO RISCO</b>', ts),
            ],
            [
                Paragraph('1°', tc), Paragraph('<b>E</b>', tc),
                Paragraph('Eliminação', tt),
                Paragraph('Eliminação total da fonte de risco', tt),
                Paragraph('<b>100%</b>', tc),
            ],
            [
                Paragraph('2°', tc), Paragraph('<b>S</b>', tc),
                Paragraph('Substituição ou Minimização', tt),
                Paragraph('Substituição de matérias-primas, equipamentos e procedimento de trabalho', tt),
                Paragraph('<b>40%</b>', tc),
            ],
            [
                Paragraph('3°', tc), Paragraph('<b>CE</b>', tc),
                Paragraph('Controle de Engenharia', tt),
                Paragraph('Enclausuramento, adaptação do ambiente de trabalho, automatização do processo', tt),
                Paragraph('<b>25%</b>', tc),
            ],
            [
                Paragraph('4°', tc), Paragraph('<b>CA</b>', tc),
                Paragraph('Controle Administrativo', tt),
                Paragraph('Sinalização, treinamentos, exames médicos, implementação de procedimento de segurança', tt),
                Paragraph('<b>15%</b>', tc),
            ],
            [
                Paragraph('5°', tc), Paragraph('<b>DP</b>', tc),
                Paragraph('Dispositivo de Proteção', tt),
                Paragraph('Uso de EPIs e implementação de EPCs', tt),
                Paragraph('<b>10%</b>', tc),
            ],
        ]
        story.extend(self._criar_tabela_padrao(
            dados_t6,
            col_widths=[1.8*cm, 1.8*cm, 3*cm, 6.9*cm, 2.5*cm],
            titulo='TABELA 6',
            subtitulo='AÇÕES A SEREM ADOTADAS DE FORMA A MITIGAR O RISCO (CRITÉRIO DE CONTROLE)\n\n'))
                        
        story.append(Paragraph(
                    "Serão priorizadas as medidas de controle coletivo dos agentes nocivos à Segurança "
                    "e Saúde dos Trabalhadores de acordo com a seguinte ordem abaixo.\n",
            self.styles['Justificado']
        ))

        story.extend(self._texto_para_paragrafos(
            "Quando, em qualquer fase do Programa, os riscos detectados ultrapassarem os "
            "valores limites das normas utilizadas, serão adotadas medidas de controle, "
            "com o objetivo de eliminar ou reduzir a exposição ao risco.\n\n"
            "Situações de risco grave e iminente serão comunicados ao supervisor da área, "
            "que deverá tomar medidas para eliminação do agente causador, sob risco de "
            "interdição do local."
        ))
        story.append(PageBreak())

        # ═══════════════════════════════════════════════
        # TABELA 7 — PRIORIZAÇÃO DAS AÇÕES
        # ═══════════════════════════════════════════════
        story.append(Paragraph("<b>TABELA 7</b>", self.styles['TituloSecao']))
        story.append(Paragraph(
            "CRITÉRIOS PARA PRIORIZAÇÃO DAS AÇÕES\n\n",
            self.styles['Justificado']))
        story.append(Paragraph(
            "Para priorização das ações será avaliado a Severidade (S) após a verificação das "
            "medidas de controle adotadas, juntamente com o grau de Probabilidade (P).\n\n",
            self.styles['Justificado']
        ))
        story.append(Spacer(1, 0.2 * cm))

        dados_t7 = [
            [
                Paragraph('<b>CLASSIFICAÇÃO DO RISCO</b>', ts),
                Paragraph('<b>PRAZO PARA AÇÕES</b>', ts),
            ],
            [Paragraph('Baixo', tc), Paragraph('Aceitável', tc)],
            [Paragraph('Tolerável', tc), Paragraph('&lt; 01 (um) ano', tc)],
            [Paragraph('Moderado', tc), Paragraph('&lt; 06 (seis) meses', tc)],
            [Paragraph('Significativo', tc), Paragraph('Paralização', tc)],
        ]

        table_t7 = Table(dados_t7, colWidths=[6*cm, 6*cm])
        table_t7.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Cores por risco
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#00ff3c")),  # Baixo
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor("#fff200")),  # Tolerável
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#ff9900")),  # Moderado
            ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor("#ff0000")),  # Significativo
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table_t7)
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph(
            "Se o risco for considerado aceitável, não será necessário adotar ações "
            "de mitigação do risco.\n"
            "Seguindo a tabela 6, pode-se identificar algumas ações que devem ser implementadas "
            "levando-se em consideração a Severidade (S) e a Probabilidade (P) do dano "
            "de acordo com a tabela 8.\n\n",
            self.styles['Justificado']
        ))
        story.append(PageBreak())

        # ═══════════════════════════════════════════════
        # TABELA 8 — MATRIZ CLASSIFICAÇÃO DO RISCO (S x P)
        # ═══════════════════════════════════════════════
        COR_B_M = colors.HexColor("#00ff3c")  # Baixo - verde claro
        COR_T_M = colors.HexColor("#fff200")  # Tolerável - amarelo claro
        COR_M_M = colors.HexColor("#ff9900")  # Moderado - laranja claro
        COR_S_M = colors.HexColor("#ff0000")  # Significativo - vermelho claro

        dados_t8 = [
            ['', Paragraph('<b>S=A</b>', ts), Paragraph('<b>S=B</b>', ts),
                Paragraph('<b>S=C</b>', ts), Paragraph('<b>S=D</b>', ts),
                Paragraph('<b>S=E</b>', ts)],
            [Paragraph('<b>P=1</b>', ts), 'B', 'B', 'B', 'T', 'T'],
            [Paragraph('<b>P=2</b>', ts), 'B', 'B', 'T', 'M', 'M'],
            [Paragraph('<b>P=3</b>', ts), 'B', 'T', 'M', 'M', 'S'],
            [Paragraph('<b>P=4</b>', ts), 'T', 'M', 'M', 'S', 'S'],
            [Paragraph('<b>P=5</b>', ts), 'T', 'M', 'S', 'S', 'S'],
        ]

        MAPA_COR_T8 = {
            'B': COR_B_M, 'T': COR_T_M, 'M': COR_M_M, 'S': COR_S_M,
        }
        matriz_t8 = [
            ['B', 'B', 'B', 'T', 'T'],
            ['B', 'B', 'T', 'M', 'M'],
            ['B', 'T', 'M', 'M', 'S'],
            ['T', 'M', 'M', 'S', 'S'],
            ['T', 'M', 'S', 'S', 'S'],
        ]
        cores_t8 = {}
        for r_idx, row in enumerate(matriz_t8):
            for c_idx, val in enumerate(row):
                cores_t8[(r_idx + 1, c_idx + 1)] = MAPA_COR_T8[val]

        story.extend(self._criar_matriz_colorida(
            dados_t8,
            col_widths=[2*cm, 2.4*cm, 2.4*cm, 2.4*cm, 2.4*cm, 2.4*cm],
            cores_celulas=cores_t8,
            titulo='TABELA 8',
            subtitulo='TABELA PARA ESTIMAR A CLASSIFICAÇÃO DO RISCO',
        ))

        # Legenda
        story.append(Paragraph(
            "<b>Legenda:</b> B = Baixo | T = Tolerável | M = Moderado | S = Significativo",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.3 * cm))

        story.extend(self._texto_para_paragrafos(
            "Caso a tabela 7 indique que para determinado risco não é necessário "
            "realizar uma ação específica, mas a empresa venha a receber uma "
            "autuação de organismo fiscalizador, ou venha acontecer algum acidente "
            "em decorrência do perigo relacionado ao risco, deve-se realizar alguma "
            "ação para minimizar esse risco, independente do resultado obtido na "
            "tabela.\n\n"
            "O plano de ação deve ser amplo e deve atender as reais necessidades "
            "de melhoria da empresa, não se prendendo somente as exigências da NR 01."
        ))

        # Exceções
        story.append(Spacer(1, 0.3 * cm))
        texto_exc = get_texto_secao(
            self.pgr, 'inventario_excecoes', nome_empresa
        )
        if texto_exc:
            story.append(Paragraph(
                "<b>EXCEÇÕES NA DEFINIÇÃO DA PERIODICIDADE DE MONITORAMENTOS</b>",
                self.styles['Normal']
            ))
            story.extend(self._texto_para_paragrafos(texto_exc))

        story.append(PageBreak())
        return story

# =============================================================================
# FUNÇÃO AUXILIAR (FORA DA CLASSE — indentação nível 0!)
# =============================================================================

def gerar_pdf_pgr(pgr_documento):
    """
    Função auxiliar para gerar o PDF do PGR.
    Se houver anexos PDF marcados com incluir_no_pdf=True,
    eles são mesclados ao final do documento.
    """
    # 1) Gerar o PDF principal do PGR via ReportLab
    generator = PGRPDFGenerator(pgr_documento)
    pdf_buffer = generator.gerar_pdf()

    # 2) Buscar anexos PDF marcados para inclusão
    anexos_pdf = AnexoPGR.objects.filter(
        pgr_documento=pgr_documento,
        incluir_no_pdf=True,
    ).order_by('ordem', 'numero_romano')

    # Filtrar apenas os que são PDF e existem no disco
    anexos_validos = []
    for anexo in anexos_pdf:
        if anexo.arquivo and anexo.arquivo.name:
            ext = anexo.arquivo.name.rsplit('.', 1)[-1].lower()
            if ext == 'pdf':
                try:
                    caminho = anexo.arquivo.path
                    if os.path.exists(caminho):
                        anexos_validos.append(anexo)
                except Exception:
                    pass

    # Se não há anexos PDF para mesclar, retorna o buffer original
    if not anexos_validos:
        return pdf_buffer

    # 3) Mesclar PDFs usando pypdf
    writer = PdfWriter()

    # Adicionar todas as páginas do PDF principal
    reader_principal = PdfReader(pdf_buffer)
    for page in reader_principal.pages:
        writer.add_page(page)

    # Para cada anexo, criar uma página de capa separadora + as páginas do PDF
    for anexo in anexos_validos:
        try:
            # --- Página separadora do anexo ---
            sep_buffer = BytesIO()
            sep_doc = SimpleDocTemplate(
                sep_buffer,
                pagesize=A4,
                leftMargin=2 * cm,
                rightMargin=2 * cm,
                topMargin=8 * cm,
                bottomMargin=2 * cm,
            )
            styles = getSampleStyleSheet()

            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.enums import TA_CENTER

            style_titulo = ParagraphStyle(
                'AnexoTitulo',
                parent=styles['Title'],
                fontSize=28,
                spaceAfter=30,
                textColor='#003366',
                alignment=TA_CENTER,
            )
            style_subtitulo = ParagraphStyle(
                'AnexoSubtitulo',
                parent=styles['Normal'],
                fontSize=16,
                spaceAfter=15,
                alignment=TA_CENTER,
                textColor='#333333',
            )
            style_tipo = ParagraphStyle(
                'AnexoTipo',
                parent=styles['Normal'],
                fontSize=12,
                alignment=TA_CENTER,
                textColor='#666666',
            )

            sep_story = [
                Paragraph(f"ANEXO {anexo.numero_romano}", style_titulo),
                Paragraph(anexo.titulo.upper(), style_subtitulo),
                Spacer(1, 0.5 * cm),
                Paragraph(anexo.get_tipo_anexo_display(), style_tipo),
                Spacer(1, 0.5 * cm),
                Paragraph(
                    f"Arquivo: {anexo.nome_arquivo_original or anexo.arquivo.name}",
                    style_tipo,
                ),
            ]

            sep_doc.build(sep_story)
            sep_buffer.seek(0)

            # Adicionar página separadora
            reader_sep = PdfReader(sep_buffer)
            for page in reader_sep.pages:
                writer.add_page(page)

            # Adicionar páginas do PDF do anexo
            reader_anexo = PdfReader(anexo.arquivo.path)
            for page in reader_anexo.pages:
                writer.add_page(page)

        except Exception as e:
            # Se falhar ao processar um anexo, pula para o próximo
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Erro ao mesclar anexo '{anexo.titulo}' (ID={anexo.pk}): {e}"
            )
            continue

    # 4) Gravar o PDF final mesclado
    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer
