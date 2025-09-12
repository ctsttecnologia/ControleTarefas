# controle_de_telefone/pdf_generator.py

import io
from django.utils.dateformat import format as date_format
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.colors import black, HexColor
from functools import partial


def get_safe_attr(obj, attrs, default='N/A'):
    """Função auxiliar para obter atributos aninhados de forma segura."""
    for attr in attrs.split('.'):
        obj = getattr(obj, attr, None)
        if obj is None:
            return default
    return obj

def gerar_termo_responsabilidade_pdf(vinculo):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontSize=11, leading=14))
    styles.add(ParagraphStyle(name='CenterBold', alignment=TA_CENTER, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))

    story = []
    
    # [MELHORIA] Usar função auxiliar para acesso seguro aos dados
    safe_get = partial(get_safe_attr, default='___________')
    
    story.append(Paragraph("TERMO DE RESPONSABILIDADE SOBRE USO DE SMARTPHONE", styles['CenterBold']))
    story.append(Spacer(1, 24))
    
    nome_contrato = safe_get(vinculo, 'funcionario.contrato.nome_contrato')
    data_entrega_f = date_format(vinculo.data_entrega, 'd \\d\\e F \\d\\e Y')
    
    texto_inicial = f"""
        A empresa <strong>CETEST MINAS ENGENHARIA E SERVIÇOS S.A</strong>, nesta data de <strong>{data_entrega_f}</strong>,
        entrega ao funcionário do <strong>{nome_contrato}</strong> um aparelho com as seguintes características:
    """
    story.append(Paragraph(texto_inicial, styles['Justify']))
    story.append(Spacer(1, 12))

    
    descricao_itens = [
        ['DESCRIÇÃO'],
        [f"1 CELULAR {safe_get(vinculo, 'aparelho.modelo.marca.nome')} {safe_get(vinculo, 'aparelho.modelo.nome')} - IMEI: {safe_get(vinculo, 'aparelho.imei')}"],
        [f"1 CHIP {safe_get(vinculo, 'linha.plano.operadora.nome')} ({safe_get(vinculo, 'linha.numero')})"],
        ["1 CABO USB/C - USB/A"],
        ["1 FONTE DE ALIMENTAÇÃO MODELO EP-TA2008"],
        ["1 CAPA CARTEIRA COR PRETO"],
        ["SMARTPHONE COM PELÍCULA DE VIDRO"],
    ]
    
    tabela_itens = Table(descricao_itens, colWidths=[450])
    tabela_itens.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), HexColor('#D9D9D9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(tabela_itens)
    story.append(Spacer(1, 12))

    # Corpo do texto - Cláusulas
    nome_completo = vinculo.funcionario.nome_completo if vinculo.funcionario else 'N/A'
    
    story.append(Paragraph(
        "O Celular de propriedade da CETEST MINAS ENGENHARIA E SERVIÇOS S.A ficará a partir desta data sob sua inteira responsabilidade, " \
        "devendo ser mantido em perfeito estado de conservação e funcionamento, " \
        "não podendo em qualquer hipótese ser cedido a terceiros sem prévia e escrita concordância da " \
        "CETEST MINAS ENGENHARIA E SERVIÇOS S.A, obedecendo as cláusulas seguintes:",
        styles['Justify']
    ))
    story.append(Spacer(1, 48))
    
    clausulas = [
        ("1-", "A CETEST MINAS ENGENHARIA E SERVIÇOS S.A NÃO autoriza o portador, ao qual este equipamento se encontra sob responsabilidade por intermédio deste termo, seja em comunicação de voz ou em transmissão de dados, receber e enviar conteúdo considerado inadequado ou ilegal, sob o ponto de vista da ética e da legislação."),
        ("2-", "Será de responsabilidade do usuário, signatário deste termo, responder por qualquer forma de comunicação que demonstre atitude de preconceito e racismo, exploração do trabalho escravo, depreciação de entidades públicas e seus servidores, assédio sexual e moral, participação em negócios exclusos aos propósitos desta empresa, descumprimento de legislação e normas reguladoras da competição saudável de mercado."),
        ("3-", f"Fica aos cuidados do(a) Sr.(a) <strong>{nome_completo}</strong> a guarda e conservação do aparelho e respectivos acessórios entregues nesta data, devendo restituí-los sempre que for solicitado pela empresa ou em caso de rescisão do contrato de trabalho, sob pena de responsabilizar-se pelo pagamento de eventuais danos materiais."),
        ("4-", "Fica vedado ao Usuário permutar o equipamento, ou qualquer um de seus acessórios, com outro usuário. Proibido a troca do e-mail e senha fornecida pela empresa."),
        ("5-", "A qualquer momento e sem prévio aviso, a empresa CETEST MINAS ENGENHARIA E SERVIÇOS S.A poderá solicitar a devolução imediata da linha e do aparelho."),
    ]

    for numero, texto in clausulas:
        p = Paragraph(f"<strong>{numero}</strong> {texto}", styles['Justify'])
        story.append(p)
        story.append(Spacer(1, 8))

    story.append(Spacer(1, 12))
    
    story.append(Paragraph(
        "Diante das cláusulas descritas neste termo e da responsabilidade que me foi confiada, declaro que recebi os equipamentos acima descritos em perfeito estado de conservação, bem como autorizo desde já o desconto em minha folha de pagamento, os valores das ligações particulares de meu exclusivo interesse bem como quaisquer outras não relacionadas com o trabalho.",
        styles['Justify']
    ))

    story.append(Spacer(1, 48))

    # Seção de Assinatura
    documento_numero = safe_get(vinculo, 'funcionario.documento.numero') 
    assinatura_texto = f"""
        ___________________________________________<br/>
        <strong>NOME:</strong> {nome_completo}<br/>
        <strong>Assinatura:</strong><br/>
        <strong>DOCUMENTO:</strong> {documento_numero}
    """
    story.append(Paragraph(assinatura_texto, styles['Center']))

    doc.build(story)
    buffer.seek(0)
    return buffer

