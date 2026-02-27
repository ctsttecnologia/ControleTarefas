
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
    NextPageTemplate
)
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from pgr_gestao.services import inicializar_secoes_pgr, get_texto_secao, get_titulo_secao

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
            for paragrafo in texto.split('\n\n'):
                paragrafo = paragrafo.strip()
                if paragrafo:
                    story.append(Paragraph(paragrafo, self.styles['Justificado']))

        # METAS
        texto_metas = get_texto_secao(self.pgr, 'documento_base_metas', nome_empresa)
        if texto_metas:
            titulo_metas = (
                get_titulo_secao(self.pgr, 'documento_base_metas') or 'METAS'
            )
            story.append(Paragraph(titulo_metas, self.styles['TituloSecao']))
            for paragrafo in texto_metas.split('\n\n'):
                paragrafo = paragrafo.strip()
                if paragrafo:
                    story.append(Paragraph(paragrafo, self.styles['Justificado']))

        # OBJETIVO GERAL
        texto_objetivo = (
            self.pgr.objetivo
            or get_texto_secao(self.pgr, 'documento_base_objetivo', nome_empresa)
        )
        if texto_objetivo:
            titulo_obj = (
                get_titulo_secao(self.pgr, 'documento_base_objetivo')
                or 'OBJETIVO GERAL'
            )
            story.append(Paragraph(titulo_obj, self.styles['TituloSecao']))
            for paragrafo in texto_objetivo.split('\n\n'):
                paragrafo = paragrafo.strip()
                if paragrafo:
                    story.append(Paragraph(paragrafo, self.styles['Justificado']))

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
                    story.append(Paragraph(
                        f"<b>{linhas[0].strip()}</b>",
                        self.styles['Normal']
                    ))
                    story.append(Paragraph(
                        linhas[1].strip(),
                        self.styles['Justificado']
                    ))
                else:
                    story.append(Paragraph(bloco, self.styles['Justificado']))

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
                for paragrafo in texto.split('\n\n'):
                    paragrafo = paragrafo.strip()
                    if paragrafo:
                        story.append(Paragraph(
                            paragrafo, self.styles['Justificado']
                        ))
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
                for paragrafo in texto.split('\n\n'):
                    paragrafo = paragrafo.strip()
                    if paragrafo:
                        story.append(Paragraph(
                            paragrafo, self.styles['Justificado']
                        ))
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

        texto = get_texto_secao(self.pgr, 'diretrizes', nome_empresa)
        if texto:
            for paragrafo in texto.split('\n\n'):
                paragrafo = paragrafo.strip()
                if paragrafo:
                    story.append(Paragraph(paragrafo, self.styles['Justificado']))
        else:
            # Texto padrão
            story.append(Paragraph("<b>ESTRATÉGIA</b>", self.styles['Normal']))
            story.append(Paragraph("<b>DIREÇÃO</b>", self.styles['Normal']))
            story.append(Paragraph(
                f"Este PGR está sendo elaborado pela área de Segurança do "
                f"Trabalho da {nome_empresa} e com apoio operacional para "
                f"implantação.",
                self.styles['Justificado']
            ))
            story.append(Paragraph(
                "<b>COLABORADORES</b>", self.styles['Normal']
            ))
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
            for paragrafo in texto.split('\n\n'):
                paragrafo = paragrafo.strip()
                if paragrafo:
                    story.append(Paragraph(paragrafo, self.styles['Justificado']))

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
            for paragrafo in texto_intro.split('\n\n'):
                paragrafo = paragrafo.strip()
                if paragrafo:
                    story.append(Paragraph(paragrafo, self.styles['Justificado']))
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
                for paragrafo in texto.split('\n\n'):
                    paragrafo = paragrafo.strip()
                    if paragrafo:
                        story.append(Paragraph(
                            paragrafo, self.styles['Justificado']
                        ))
                story.append(Spacer(1, 0.3 * cm))

        story.append(PageBreak())
        return story

    # =================================================================
    # 9. INVENTÁRIO DE RISCOS
    # =================================================================

    def _criar_inventario_riscos(self):
        """Cria o inventário de riscos conforme PDF modelo oficial (13 colunas)"""
        story = []
        story.append(Paragraph(
            "9. INVENTÁRIO DE RISCOS, PERIGOS, ASPECTOS E IMPACTOS",
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

            # AVALIAÇÕES QUANTITATIVAS
            avaliacoes = []
            for risco in riscos:
                for av in risco.avaliacoes_quantitativas.all():
                    avaliacoes.append(av)

            if avaliacoes:
                story.append(Paragraph(
                    "<b>AVALIAÇÕES QUANTITATIVAS</b>",
                    self.styles['Normal']
                ))
                story.append(Spacer(1, 0.2 * cm))

                for avaliacao in avaliacoes:
                    conformidade = (
                        'Conforme' if avaliacao.conforme else 'Não Conforme'
                    )
                    texto_avaliacao = (
                        f"<b>{avaliacao.get_tipo_avaliacao_display()}:</b> "
                        f"Resultado: {avaliacao.resultado_medido} "
                        f"{avaliacao.unidade_medida} | "
                        f"Data: {avaliacao.data_avaliacao.strftime('%d/%m/%Y')} | "
                        f"Conformidade: {conformidade} | "
                        f"Equipamento: "
                        f"{avaliacao.equipamento_utilizado or 'N/A'}"
                    )
                    story.append(Paragraph(
                        texto_avaliacao, self.styles['TabelaTexto']
                    ))
                    story.append(Spacer(1, 0.2 * cm))

            story.append(PageBreak())

        return story

    # =================================================================
    # 10. PLANO DE AÇÃO (texto)
    # =================================================================

    def _criar_plano_acao_texto(self):
        """Cria a seção 10 - Plano de Ação (texto introdutório)"""
        nome_empresa = self._get_nome_empresa()
        story = []

        titulo = (
            get_titulo_secao(self.pgr, 'plano_acao') or '10. PLANO DE AÇÃO'
        )
        story.append(Paragraph(titulo, self.styles['TituloSecao']))

        texto = get_texto_secao(self.pgr, 'plano_acao', nome_empresa)
        if texto:
            for paragrafo in texto.split('\n\n'):
                paragrafo = paragrafo.strip()
                if paragrafo:
                    story.append(Paragraph(paragrafo, self.styles['Justificado']))

        story.append(PageBreak())
        return story

    # =================================================================
    # 11. MEDIDAS DE PROTEÇÃO
    # =================================================================

    def _criar_medidas_protecao(self):
        """Cria a seção 11 - Medidas de Proteção"""
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
                for paragrafo in texto.split('\n\n'):
                    paragrafo = paragrafo.strip()
                    if paragrafo:
                        story.append(Paragraph(
                            paragrafo, self.styles['Justificado']
                        ))
                story.append(Spacer(1, 0.3 * cm))

        story.append(PageBreak())
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
        story.append(PageBreak())
        return story

    # =================================================================
    # 13. DIVULGAÇÃO
    # =================================================================

    def _criar_divulgacao(self):
        """Cria a seção 13 - Divulgação do Programa"""
        nome_empresa = self._get_nome_empresa()
        story = []

        titulo = (
            get_titulo_secao(self.pgr, 'divulgacao')
            or '13. DIVULGAÇÃO DO PROGRAMA'
        )
        story.append(Paragraph(titulo, self.styles['TituloSecao']))

        texto = get_texto_secao(self.pgr, 'divulgacao', nome_empresa)
        if texto:
            for paragrafo in texto.split('\n\n'):
                paragrafo = paragrafo.strip()
                if paragrafo:
                    story.append(Paragraph(paragrafo, self.styles['Justificado']))

        story.append(PageBreak())
        return story

    # =================================================================
    # 14. RECOMENDAÇÕES
    # =================================================================

    def _criar_recomendacoes(self):
        """Cria a seção 14 - Recomendações Gerais"""
        nome_empresa = self._get_nome_empresa()
        story = []

        titulo = (
            get_titulo_secao(self.pgr, 'recomendacoes')
            or '14. RECOMENDAÇÕES GERAIS'
        )
        story.append(Paragraph(titulo, self.styles['TituloSecao']))

        texto = get_texto_secao(self.pgr, 'recomendacoes', nome_empresa)
        if texto:
            for paragrafo in texto.split('\n\n'):
                paragrafo = paragrafo.strip()
                if paragrafo:
                    story.append(Paragraph(paragrafo, self.styles['Justificado']))

        story.append(PageBreak())
        return story

    # =================================================================
    # 15. LEGISLAÇÃO
    # =================================================================

    def _criar_legislacao(self):
        """Cria a seção 15 - Legislação Complementar"""
        nome_empresa = self._get_nome_empresa()
        story = []

        titulo = (
            get_titulo_secao(self.pgr, 'legislacao')
            or '15. LEGISLAÇÃO COMPLEMENTAR'
        )
        story.append(Paragraph(titulo, self.styles['TituloSecao']))

        texto = get_texto_secao(self.pgr, 'legislacao', nome_empresa)
        if texto:
            for paragrafo in texto.split('\n\n'):
                paragrafo = paragrafo.strip()
                if paragrafo:
                    story.append(Paragraph(paragrafo, self.styles['Justificado']))

        story.append(PageBreak())
        return story

    # =================================================================
    # ASSINATURAS
    # =================================================================

    def _criar_pagina_assinaturas(self):
        """Cria a página de assinaturas"""
        story = []
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

        # ===== FRAMES =====
        frame_capa = Frame(
            2.5 * cm,
            2 * cm,
            width - 4 * cm,
            height - 5 * cm,
            id='frame_capa'
        )

        frame_normal = Frame(
            1.5 * cm,
            2 * cm,
            width - 3 * cm,
            height - 4.5 * cm,
            id='frame_normal'
        )

        # ===== PAGE TEMPLATES =====
        # Funções de callback são funções de módulo (fora da classe)
        template_capa = PageTemplate(
            id='capa',
            frames=[frame_capa],
            onPage=draw_capa_background,
        )

        template_normal = PageTemplate(
            id='normal',
            frames=[frame_normal],
            onPage=draw_header_footer,
        )

        doc.addPageTemplates([template_capa, template_normal])

        # ===== MONTAR STORY =====
        story = []

        # CAPA (inclui NextPageTemplate('normal') + PageBreak no final)
        story.extend(self._criar_capa())

        # DEMAIS SEÇÕES (todas usam template 'normal')
        story.extend(self._criar_caracterizacao_empresa())
        story.extend(self._criar_controle_revisao())
        story.extend(self._criar_documento_base())
        story.extend(self._criar_definicoes())
        story.extend(self._criar_estrutura_pgr())
        story.extend(self._criar_responsabilidades())
        story.extend(self._criar_diretrizes())
        story.extend(self._criar_desenvolvimento())
        story.extend(self._criar_metodologia())
        story.extend(self._criar_inventario_riscos())
        story.extend(self._criar_plano_acao_texto())
        story.extend(self._criar_medidas_protecao())
        story.extend(self._criar_cronograma_acoes())
        story.extend(self._criar_divulgacao())
        story.extend(self._criar_recomendacoes())
        story.extend(self._criar_legislacao())
        story.extend(self._criar_pagina_assinaturas())

        # ===== BUILD =====
        doc.build(story)
        buffer.seek(0)
        return buffer


# =============================================================================
# FUNÇÃO AUXILIAR (FORA DA CLASSE)
# =============================================================================

def gerar_pdf_pgr(pgr_documento):
    """Função auxiliar para gerar o PDF do PGR"""
    generator = PGRPDFGenerator(pgr_documento)
    return generator.gerar_pdf()


