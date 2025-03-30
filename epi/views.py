from django.shortcuts import render, redirect, get_object_or_404
from .models import FichaEPI, ItemEPI, EPI
from .forms import FichaEPIForm, ItemEPIForm
from django.contrib.auth.decorators import login_required
from reportlab.pdfgen import canvas
from io import BytesIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from docx import Document
from docx.shared import Inches

@login_required
def criar_ficha(request):
    if request.method == 'POST':
        form_ficha = FichaEPIForm(request.POST, request.FILES)
        form_item = ItemEPIForm(request.POST)
        
        if form_ficha.is_valid() and form_item.is_valid():
            ficha = form_ficha.save(commit=False)
            ficha.empregado = request.user  # Associa automaticamente ao usuário logado
            ficha.save()
            
            item = form_item.save(commit=False)
            item.ficha = ficha
            item.save()
            return redirect('listar_fichas')
    else:
        form_ficha = FichaEPIForm(initial={'empregado': request.user})
        form_item = ItemEPIForm()

    return render(request, 'epi/criar_ficha.html', {
        'form_ficha': form_ficha,
        'form_item': form_item,
    })

@login_required
def listar_fichas(request):
    fichas = FichaEPI.objects.filter(empregado=request.user).prefetch_related('itens')
    return render(request, 'epi/listar_fichas.html', {'fichas': fichas})

@login_required
def visualizar_ficha(request, ficha_id):
    ficha = get_object_or_404(FichaEPI, id=ficha_id, empregado=request.user)
    itens = ficha.itens.all()
    return render(request, 'epi/visualizar_ficha.html', {'ficha': ficha, 'itens': itens})

@login_required
def gerar_pdf(request, ficha_id):
    ficha = get_object_or_404(FichaEPI, id=ficha_id, empregado=request.user)
    itens = ficha.itens.all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Cabeçalho
    elements.append(Paragraph("FICHA DE CONTROLE DE EPI's", styles['Title']))
    elements.append(Paragraph("Dados de Identificação", styles['Heading2']))
    
    # Dados do empregado
    data_empregado = [
        ["Empregado:", ficha.empregado.get_full_name()],
        ["Cargo:", ficha.cargo],
        ["Registro:", ficha.registro],
        ["Admissão:", ficha.admissao.strftime('%d/%m/%Y')],
        ["Demissão:", ficha.demissao.strftime('%d/%m/%Y') if ficha.demissao else "N/A"],
        ["Contrato:", ficha.contrato],
    ]
    
    t = Table(data_empregado, colWidths=[1.5*inch, 4*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(t)
    
    # Termo de compromisso
    elements.append(Paragraph("TERMO DE COMPROMISSO", styles['Heading2']))
    termo_texto = [
        f"Eu, {ficha.empregado.get_full_name()},",
        "Declaro, que recebi de CETEST MINAS ENGENHARIA E SERVIÇOS S/A, os Equipamentos de Proteção",
        "Individual - EPI's - abaixo relacionados, comprometendo-me a:",
        "1) - Usá-los em trabalho, zelando pela sua guarda e conservação, devolvendo-os quando se tornarem",
        "impróprios para o uso e/ou meu desligamento da CETEST MINAS ou do seu respectivo contrato;",
        "2) - Em caso de perda, mau uso, extravio ou inutilização proposital do EPI recebido, assumo a",
        "responsabilidade Quanto à restituição do seu valor atualizado, conforme autorização de débito por mim assinada.",
        "Declaro ainda ter recebido no ato de minha admissão e no ato do recebimento:",
        "1) Treinamento básico e instruções prévias sobre a forma de utilização e guarda dos EPI's recebido;",
        "2) Instruções sobre os riscos a que estou exposto em minha área de trabalho, bem como sua prevenção.",
        "3) Estou ciente de que o não uso dos EPI's, constitui ato faltoso conforme artigo 158 da CLT.",
        "",
        f"Local e Data: {ficha.local_data}",
        "Assinatura: ___________________________________________",
    ]
    
    for linha in termo_texto:
        elements.append(Paragraph(linha, styles['Normal']))
    
    # Tabela de EPIs
    elements.append(Paragraph("RECEBIMENTO / DEVOLUÇÃO", styles['Heading2']))
    
    dados_tabela = [["Data", "Qtde.", "Un.", "Descrição EPI", "Certificado Aprovação", "Assinatura"]]
    
    for item in itens:
        dados_tabela.append([
            item.data_recebimento.strftime('%d/%m/%Y'),
            str(item.quantidade),
            item.epi.unidade,
            item.epi.nome,
            item.epi.certificado,
            "_________________________"
        ])
    
    t = Table(dados_tabela, colWidths=[0.8*inch, 0.5*inch, 0.5*inch, 2.5*inch, 1.2*inch, 1*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
    ]))
    elements.append(t)
    
    # Artigo CLT
    elements.append(Paragraph("CONSOLIDAÇÃO DAS LEIS DO TRABALHO", styles['Heading2']))
    elements.append(Paragraph("Art. 158 - Cabe aos empregados", styles['Normal']))
    elements.append(Paragraph("I - Observar as normas de segurança e medicina do trabalho, inclusive as instruções de que trata o item II do artigo anterior;", styles['Normal']))
    elements.append(Paragraph("II-Colaborar com a empresa na aplicação dos dispositivos deste capítulo.", styles['Normal']))
    elements.append(Paragraph("Parágrafo Único: Constitui ato faltoso do empregado a recusa injustificada:", styles['Normal']))
    elements.append(Paragraph("a) ...", styles['Normal']))
    elements.append(Paragraph("b) ao uso dos equipamentos de proteção individual fornecidos pela empresa.", styles['Normal']))
    
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ficha_epi_{ficha.empregado.username}.pdf"'
    
    return response

@login_required
def gerar_word(request, ficha_id):
    ficha = get_object_or_404(FichaEPI, id=ficha_id, empregado=request.user)
    itens = ficha.itens.all()

    document = Document()
    
    # Cabeçalho
    document.add_heading('FICHA DE CONTROLE DE EPI\'s', 0)
    document.add_heading('Dados de Identificação', level=2)
    
    # Dados do empregado
    dados = [
        ("Empregado:", ficha.empregado.get_full_name()),
        ("Cargo:", ficha.cargo),
        ("Registro:", ficha.registro),
        ("Admissão:", ficha.admissao.strftime('%d/%m/%Y')),
        ("Demissão:", ficha.demissao.strftime('%d/%m/%Y') if ficha.demissao else "N/A"),
        ("Contrato:", ficha.contrato),
    ]
    
    table = document.add_table(rows=0, cols=2)
    for label, value in dados:
        row = table.add_row().cells
        row[0].text = label
        row[1].text = value
    
    # Termo de compromisso
    document.add_heading('TERMO DE COMPROMISSO', level=2)
    termo = document.add_paragraph()
    termo.add_run(f"Eu, {ficha.empregado.get_full_name()},\n")
    termo.add_run("Declaro, que recebi de CETEST MINAS ENGENHARIA E SERVIÇOS S/A, os Equipamentos de Proteção\n")
    termo.add_run("Individual - EPI's - abaixo relacionados, comprometendo-me a:\n")
    termo.add_run("1) - Usá-los em trabalho, zelando pela sua guarda e conservação, devolvendo-os quando se tornarem\n")
    termo.add_run("impróprios para o uso e/ou meu desligamento da CETEST MINAS ou do seu respectivo contrato;\n")
    termo.add_run("2) - Em caso de perda, mau uso, extravio ou inutilização proposital do EPI recebido, assumo a\n")
    termo.add_run("responsabilidade Quanto à restituição do seu valor atualizado, conforme autorização de débito por mim assinada.\n")
    termo.add_run("Declaro ainda ter recebido no ato de minha admissão e no ato do recebimento:\n")
    termo.add_run("1) Treinamento básico e instruções prévias sobre a forma de utilização e guarda dos EPI's recebido;\n")
    termo.add_run("2) Instruções sobre os riscos a que estou exposto em minha área de trabalho, bem como sua prevenção.\n")
    termo.add_run("3) Estou ciente de que o não uso dos EPI's, constitui ato faltoso conforme artigo 158 da CLT.\n\n")
    termo.add_run(f"Local e Data: {ficha.local_data}\n")
    termo.add_run("Assinatura: ___________________________________________\n")
    
    # Tabela de EPIs
    document.add_heading('RECEBIMENTO / DEVOLUÇÃO', level=2)
    
    table = document.add_table(rows=1, cols=6)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Data'
    hdr_cells[1].text = 'Qtde.'
    hdr_cells[2].text = 'Un.'
    hdr_cells[3].text = 'Descrição EPI'
    hdr_cells[4].text = 'Certificado Aprovação'
    hdr_cells[5].text = 'Assinatura'
    
    for item in itens:
        row_cells = table.add_row().cells
        row_cells[0].text = item.data_recebimento.strftime('%d/%m/%Y')
        row_cells[1].text = str(item.quantidade)
        row_cells[2].text = item.epi.unidade
        row_cells[3].text = item.epi.nome
        row_cells[4].text = item.epi.certificado
        row_cells[5].text = "_________________________"
    
    # Artigo CLT
    document.add_heading('CONSOLIDAÇÃO DAS LEIS DO TRABALHO', level=2)
    document.add_paragraph('Art. 158 - Cabe aos empregados', style='ListBullet')
    document.add_paragraph('I - Observar as normas de segurança e medicina do trabalho, inclusive as instruções de que trata o item II do artigo anterior;', style='ListBullet2')
    document.add_paragraph('II-Colaborar com a empresa na aplicação dos dispositivos deste capítulo.', style='ListBullet2')
    document.add_paragraph('Parágrafo Único: Constitui ato faltoso do empregado a recusa injustificada:', style='ListBullet2')
    document.add_paragraph('a) ...', style='ListBullet3')
    document.add_paragraph('b) ao uso dos equipamentos de proteção individual fornecidos pela empresa.', style='ListBullet3')
    
    # Salvar o documento
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename="ficha_epi_{ficha.empregado.username}.docx"'
    
    return response
