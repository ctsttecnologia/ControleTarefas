
# controle_de_telefone/pdf_generator.py

import io
from django.utils.dateformat import format
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.colors import black

def gerar_termo_responsabilidade_pdf(vinculo):
    """
    Gera o Termo de Responsabilidade em PDF para um determinado vínculo.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))

    story = []

    # Título
    story.append(Paragraph("TERMO DE RESPONSABILIDADE SOBRE USO DE SMARTPHONE", styles['h1']))
    story.append(Spacer(1, 24))

    # Data Formatada
    data_formatada = format(vinculo.data_entrega, 'd \de F \de Y')
    
    # Parágrafo inicial
    texto_inicial = f"""
        A empresa <strong>CETEST MINAS ENGENHARIA E SERVIÇOS S.A</strong>, nesta data de {data_formatada},
        entrega ao funcionário do CM <strong>{vinculo.funcionario.contrato or 'N/A'}</strong> um aparelho com as seguintes características:
    """
    story.append(Paragraph(texto_inicial, styles['Justify']))
    story.append(Spacer(1, 12))

    # Tabela com a descrição dos itens
    descricao_itens = [
        ['DESCRIÇÃO DOS ITENS RECEBIDOS'],
    ]
    if vinculo.aparelho:
        descricao_itens.append([f"1 CELULAR {vinculo.aparelho.marca} {vinculo.aparelho.modelo} - IMEI: {vinculo.aparelho.imei}"])
    if vinculo.linha:
        descricao_itens.append([f"1 CHIP {vinculo.linha.operadora} ({vinculo.linha.numero})"])
    
    # Adicione outros itens fixos ou variáveis aqui, se necessário
    descricao_itens.append(["1 CABO USB-C / USB-A"])
    descricao_itens.append(["1 FONTE DE ALIMENTAÇÃO"])
    descricao_itens.append(["SMARTPHONE COM PELÍCULA DE VIDRO"])
    
    tabela_itens = Table(descricao_itens, colWidths=[450])
    tabela_itens.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#CCCCCC'),
        ('TEXTCOLOR', (0, 0), (-1, 0), black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), '#F7F7F7'),
        ('GRID', (0, 0), (-1, -1), 1, black)
    ]))
    story.append(tabela_itens)
    story.append(Spacer(1, 12))

    # Corpo do texto - Cláusulas (extraídas do documento original)
    clausulas = [
        "O Celular de propriedade da CETEST MINAS ENGENHARIA E SERVIÇOS S.A ficará a partir desta data sob sua inteira responsabilidade, devendo ser mantido em perfeito estado de conservação e funcionamento, não podendo em qualquer hipótese ser cedido a terceiros sem prévia e escrita concordância da CETEST MINAS ENGENHARIA E SERVIÇOS S.A.",
        "Será de responsabilidade do usuário, signatário deste termo, responder por qualquer forma de comunicação que demonstre atitude de preconceito e racismo, exploração do trabalho escravo, assédio sexual e moral, ou descumprimento de legislação.",
        f"Fica aos cuidados do(a) Sr.(a) <strong>{vinculo.funcionario.nome_completo}</strong> a guarda e conservação do aparelho e respectivos acessórios entregues nesta data, devendo restituí-los sempre que for solicitado pela empresa ou em caso de rescisão do contrato de trabalho.",
        "Fica vedado ao Usuário permutar o equipamento, ou qualquer um de seus acessórios, com outro usuário.",
        "É proibida a troca do e-mail e senha fornecida pela empresa.",
        "A qualquer momento e sem prévio aviso, a empresa CETEST MINAS ENGENHARIA E SERVIÇOS S.A poderá solicitar a devolução imediata da linha e do aparelho.",
        "Diante das cláusulas descritas neste termo, declaro que recebi os equipamentos acima descritos em perfeito estado de conservação, bem como autorizo desde já o desconto em minha folha de pagamento, os valores das ligações particulares de meu exclusivo interesse bem como quaisquer outras não relacionadas com o trabalho.",
    ]
    
    for clausula in clausulas:
        story.append(Paragraph(clausula, styles['Justify']))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 48))

    # Seção de Assinatura
    assinatura_texto = f"""
        ___________________________________________<br/>
        <strong>NOME:</strong> {vinculo.funcionario.nome_completo}<br/>
        <strong>RG:</strong> {vinculo.funcionario.rg or 'N/A'}
    """
    story.append(Paragraph(assinatura_texto, styles['Center']))

    doc.build(story)
    buffer.seek(0)
    return buffer
