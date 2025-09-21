# controle_de_telefone/pdf_utils.py


import io
from functools import partial
import logging
import os
from django.contrib.staticfiles import finders
from django.utils.dateformat import format as date_format
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
from departamento_pessoal.models import Documento

logger = logging.getLogger(__name__)

# --- FUNÇÕES DE AUXÍLIO ---

def get_safe_attr(obj, attrs, default='N/A'):
    """
    Função auxiliar para obter atributos aninhados de forma segura.
    Retorna o valor padrão se qualquer atributo na cadeia for None ou vazio.
    """
    for attr in attrs.split('.'):
        try:
            obj = getattr(obj, attr, None)
            if callable(obj): # Lida com métodos, como 'get_tipo_aparelho_display'
                obj = obj()
            
            if obj is None or (isinstance(obj, str) and not obj.strip()):
                return default
        except AttributeError:
            return default
    return obj if obj else default

def get_reportlab_styles():
    """Define e retorna os estilos de parágrafo personalizados."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontSize=10, leading=12))
    styles.add(ParagraphStyle(name='CenterBold', alignment=TA_CENTER, fontName='Helvetica-Bold', fontSize=12))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, fontSize=10))
    styles.add(ParagraphStyle(name='CenterSmall', alignment=TA_CENTER, fontSize=8))
    return styles

# --- FUNÇÕES DE CRIAÇÃO DE CONTEÚDO PARA O PDF ---

def create_header(vinculo, styles, safe_get): # <-- CORREÇÃO 1: Adicionado 'safe_get'
    """Cria a seção do cabeçalho com título e logo lado a lado usando uma Tabela."""
    
    # 1. Prepara o conteúdo do título
    tipo_aparelho = get_safe_attr(vinculo, 'aparelho.get_tipo_aparelho_display', default='Aparelho')
    
    texto_titulo = f"TERMO DE RESPONSABILIDADE<br/>SOBRE USO DE <strong>{tipo_aparelho.upper()}</strong>"
    titulo_paragraph = Paragraph(texto_titulo, styles['CenterBold'])
    
    # 2. Prepara o conteúdo da logo
    logo_content = Spacer(0, 0)
    caminho_logo = finders.find('images/logocetest.png')
    if caminho_logo:
        logo_content = Image(caminho_logo, width=120, height=48)
    else:
        logger.warning("AVISO: Logo 'images/logocetest.png' não encontrada.")
        
    # 3. Organiza os conteúdos em uma tabela
    data = [[titulo_paragraph, logo_content]]
    table = Table(data, colWidths=['75%', '25%'])
    
    # 4. Aplica um estilo à tabela
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
    ]))
    
    return [table, Spacer(1, 20)]

def create_introductory_text(vinculo, styles, safe_get):
    """Cria a seção do texto introdutório do termo."""
    EMPRESA_NOME = "CETEST MINAS ENGENHARIA E SERVIÇOS S.A"
    data_entrega_f = date_format(vinculo.data_entrega, 'd \\d\\e F \\d\\e Y')
    texto_inicial = f"""
        A empresa <strong>{EMPRESA_NOME}</strong>, nesta data de <strong>{data_entrega_f}</strong>,
        entrega ao funcionário do contrato CM {safe_get(vinculo, 'funcionario.cliente.contrato')} um aparelho com as seguintes características:
    """
    return [Paragraph(texto_inicial, styles['Justify']), Spacer(1, 10)]

def create_item_table(vinculo, safe_get):
    """Cria a tabela de itens entregues."""
    descricao_itens = [
        ['DESCRIÇÃO DOS ITENS ENTREGUES'],
        [f"1 CELULAR {safe_get(vinculo, 'aparelho.modelo.marca.nome')} {safe_get(vinculo, 'aparelho.modelo.nome')} - IMEI: {safe_get(vinculo, 'aparelho.imei')}"],
        [f"1 CHIP {safe_get(vinculo, 'linha.plano.operadora.nome')} ({safe_get(vinculo, 'linha.numero')})"],
        [f"1 ACESSÓRIO: {safe_get(vinculo, 'aparelho.acessorios')}"],
    ]
    tabela_itens = Table(descricao_itens, colWidths=['100%'])
    tabela_itens.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D9D9D9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return [tabela_itens, Spacer(1, 10)]

def create_clauses_section(vinculo, styles, safe_get):
    """Cria a seção das cláusulas do termo."""
    EMPRESA_NOME = "CETEST MINAS ENGENHARIA E SERVIÇOS S.A"
    clausulas_intro = f"""
        O <strong>{safe_get(vinculo, 'aparelho.tipo_de_aparelho')}</strong> de propriedade da {EMPRESA_NOME} ficará a partir desta data sob sua inteira responsabilidade, 
        devendo ser mantido em perfeito estado de conservação e funcionamento, 
        não podendo em qualquer hipótese ser cedido a terceiros sem prévia e escrita concordância da {EMPRESA_NOME},
        obedecendo as cláusulas seguintes:
    """
    story = [Paragraph(clausulas_intro, styles['Justify']), Spacer(1, 10)]
    
    clausulas = [
        ("1-", "A empresa NÃO autoriza o portador a receber e enviar conteúdo inadequado ou ilegal."),
        ("2-", "Será de responsabilidade do usuário responder por qualquer forma de comunicação que demonstre preconceito, assédio, ou participação em negócios exclusos aos propósitos da empresa."),
        ("3-", f"Fica aos cuidados do(a) Sr.(a) <strong>{safe_get(vinculo, 'funcionario.nome_completo')}</strong> a guarda e conservação do aparelho e acessórios, devendo restituí-los quando solicitado ou em caso de rescisão, sob pena de responsabilizar-se por danos."),
        ("4-", "Fica vedado permutar o equipamento ou seus acessórios. É proibida a troca do e-mail e senha fornecida pela empresa."),
        ("5-", f"A qualquer momento e sem prévio aviso, a {EMPRESA_NOME} poderá solicitar a devolução imediata da linha e do aparelho."),
    ]
    for numero, texto in clausulas:
        story.append(Paragraph(f"<strong>{numero}</strong> {texto}", styles['Justify']))
        story.append(Spacer(1, 5))
        
    return story

def create_signature_block(vinculo, styles, safe_get):
    """
    Cria a tabela de assinaturas, incluindo a assinatura digital se existir.
    """
    assinatura_story_content = []

    # PASSO 1: Verificar se há uma assinatura digital salva
    if hasattr(vinculo, 'assinatura_digital') and vinculo.assinatura_digital:
        assinatura_path = vinculo.assinatura_digital.path
        
        # PASSO 2: Verificar se o arquivo da assinatura existe no disco
        if os.path.exists(assinatura_path):
            try:
                assinatura_img = Image(assinatura_path, width=150, height=50)
                assinatura_story_content.append(assinatura_img)
            except Exception as e:
                logger.error(f"Erro ao carregar imagem da assinatura: {e}")
                assinatura_story_content.append(Paragraph("________________________________", styles['Center']))
        else:
            logger.warning(f"Assinatura não encontrada em: {assinatura_path}")
            assinatura_story_content.append(Paragraph("________________________________", styles['Center']))
    else:
        logger.info("Nenhuma assinatura digital encontrada para este vínculo.")
        assinatura_story_content.append(Paragraph("________________________________", styles['Center']))

    # Adiciona nome e documento abaixo da linha/imagem
    assinatura_story_content.append(Spacer(1, 2))
    assinatura_story_content.append(Paragraph(safe_get(vinculo, 'funcionario.nome_completo'), styles['Center']))
    
    # Busca o RG do funcionário
    try:
        rg_doc = Documento.objects.get(funcionario=vinculo.funcionario, tipo_documento='RG')
        rg_numero = rg_doc.numero
    except Documento.DoesNotExist:
        rg_numero = "N/A"
    assinatura_story_content.append(Paragraph(f"RG: {rg_numero}", styles['CenterSmall']))

    tabela = Table([[assinatura_story_content]], colWidths=['100%'])
    tabela.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    
    return [Spacer(1, 25), KeepTogether([tabela])]


# --- FUNÇÃO PRINCIPAL ---
def gerar_termo_pdf_assinado(vinculo):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=40, bottomMargin=40)

    styles = get_reportlab_styles()
    safe_get = partial(get_safe_attr, default='___________')
    story = []

    story.extend(create_header(vinculo, styles, safe_get))
    story.extend(create_introductory_text(vinculo, styles, safe_get))
    story.extend(create_item_table(vinculo, safe_get))
    story.extend(create_clauses_section(vinculo, styles, safe_get))

    declaracao = "Diante das cláusulas descritas..." # (mantenha seu texto de declaração)
    story.append(Spacer(1, 10))
    story.append(Paragraph(declaracao, styles['Justify']))
    
    # Bloco de Assinaturas (agora com a imagem)
    story.extend(create_signature_block(vinculo, styles, safe_get))

    doc.build(story)
    buffer.seek(0)
    return buffer
