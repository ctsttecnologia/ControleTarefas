
# ltcat/texto_padrao.py

"""
Textos fixos padrão do LTCAT — fielmente baseados no modelo Word oficial.
Variáveis entre {chaves} são substituídas em tempo de geração.
"""


# =============================================================================
# SEÇÃO 2 — OBJETIVO
# =============================================================================

OBJETIVO = (
    "O LTCAT tem por finalidade cumprir as exigências da legislação previdenciária "
    "- Art. 58 da Lei nº 9528 de 10.12.97, dar sustentabilidade técnica às condições "
    "ambientais existentes na empresa e subsidiar o enquadramento de tais atividades "
    "referente ao recolhimento das denominadas Alíquotas Suplementares do Seguro de "
    "Acidentes do Trabalho (SAT) criadas pelo texto da Lei nº 9.732 de 11.12.98, e "
    "convertida em Lei nº 9528 de 10.12.97.\n\n"
    "Art. 58 - § 1º A comprovação da efetiva exposição do segurado aos agentes nocivos "
    "será feita mediante formulário, na forma estabelecida pelo Instituto Nacional do "
    "Seguro Social - INSS, emitido pela empresa ou seu preposto, com base em laudo "
    "técnico de condições ambientais do trabalho expedido por médico do trabalho ou "
    "engenheiro de segurança do trabalho nos termos da legislação trabalhista.\n\n"
    "§ 2º Do laudo técnico referido no parágrafo anterior deverão constar informação "
    "sobre a existência de tecnologia de proteção coletiva ou individual que diminua a "
    "intensidade do agente agressivo a limites de tolerância e recomendação sobre a sua "
    "adoção pelo estabelecimento respectivo."
)


# =============================================================================
# SEÇÃO 3 — CONDIÇÕES PRELIMINARES
# =============================================================================

CONDICOES_PRELIMINARES = (
    "O trabalho de levantamento de dados foi realizado no local da prestação de serviços."
)


# =============================================================================
# SEÇÃO 4 — CÓDIGOS DO SISTEMA SEFIP / GFIP
# =============================================================================

CODIGOS_GFIP = (
    "Para classificação da ocorrência, deve ser consultada a tabela de classificação "
    "dos Agentes Nocivos (Anexo IV do regulamento da Previdência Social, aprovado pelo "
    "Decreto 3048/99). Para comprovar que o trabalhador está exposto a agentes nocivos "
    "é necessário que a empresa mantenha o Perfil Profissiográfico Previdenciário (PPP), "
    "conforme disposto no art. 58, da Lei 8213/91.\n\n"
    "GFIP – Guia do Recolhimento do Fundo de Garantia por Tempo de Serviço e Informações "
    "Previdenciárias, instituído pela Lei 9.528 de 10/12/97.\n\n"
    "Para trabalhadores com apenas um vínculo empregatício (ou uma fonte pagadora):\n\n"
    "Código 00 - Indicativo de não ter havido em nenhum momento exposição a qualquer "
    "agente nocivo. Trabalhador nunca esteve exposto.\n"
    "Código 01 - Indicativo de ter havido em algum momento exposição a algum agente "
    "nocivo, mas posteriormente devidamente neutralizado.\n"
    "Código 02 - Indicativo de exposição dos trabalhadores a algum agente nocivo "
    "(aposentadoria especial aos 15 anos de trabalho).\n"
    "Código 03 - Indicativo de exposição dos trabalhadores a algum agente nocivo "
    "(aposentadoria especial aos 20 anos de trabalho).\n"
    "Código 04 - Indicativo de exposição dos trabalhadores a algum agente nocivo "
    "(aposentadoria especial aos 25 anos de trabalho).\n\n"
    "REPERCUSSÃO ECONÔMICA:\n\n"
    "0 e 1 - Não há incidência de alíquota suplementar;\n"
    "2 - Alíquota suplementar de 12% sobre o salário bruto dos trabalhadores;\n"
    "3 - Alíquota suplementar de 9% sobre o salário bruto dos trabalhadores;\n"
    "4 - Alíquota suplementar de 6% sobre o salário bruto dos trabalhadores.\n\n"
    "PARA TRABALHADORES COM MAIS DE UM VÍNCULO EMPREGATÍCIO "
    "(ou mais de uma fonte pagadora):\n\n"
    "Código 05 - Indicativo de não ter havido em nenhum momento exposição a qualquer "
    "agente nocivo. Trabalhador nunca esteve exposto.\n"
    "Código 06 - Indicativo de exposição dos trabalhadores a algum agente nocivo "
    "(aposentadoria especial aos 15 anos de trabalho).\n"
    "Código 07 - Indicativo de exposição dos trabalhadores a algum agente nocivo "
    "(aposentadoria especial aos 20 anos de trabalho).\n"
    "Código 08 - Indicativo de exposição dos trabalhadores a algum agente nocivo "
    "(aposentadoria especial aos 25 anos de trabalho).\n\n"
    "Para classificação da ocorrência, deve ser consultada a tabela de classificação "
    "dos Agentes Nocivos (Anexo IV do regulamento da Previdência Social, aprovado pelo "
    "Decreto 3048/99). Para comprovar que o trabalhador está exposto a agentes nocivos "
    "é necessário que a empresa mantenha o perfil profissiográfico previdenciário (PPP), "
    "conforme disposto no art. 58, da Lei 8213/91."
)

TRABALHO_PERMANENTE = (
    "Trabalho Permanente: É aquele em que o segurado, no exercício de suas funções, "
    "está exposto efetivamente a agentes nocivos: físicos, químicos e biológicos ou "
    "associação destes.\n\n"
    "Trabalho não Ocasional nem Intermitente: É aquele em que na jornada de trabalho "
    "não houve interrupção ou suspensão do exercício de atividade com exposição aos "
    "agentes nocivos, ou seja, não foi exercida de forma alternada atividade comum "
    "com especial.\n\n"
    "Indissociável: aquilo que é inseparável, que não pode ser separado."
)

AGENTES_NOCIVOS = (
    "Conforme expresso no Art. 156, são consideradas condições especiais que prejudicam "
    "a saúde ou a integridade física, conforme definido no Anexo IV do RPS, aprovado "
    "pelo Decreto 3.048/99, a exposição a agentes nocivos químicos, físicos ou biológicos "
    "a exposição à associação desses agentes, em concentração ou intensidade e tempo de "
    "exposição que ultrapasse os limites de tolerância ou que, dependendo do agente, torne "
    "a simples exposição em condição especial prejudicial à saúde.\n\n"
    "Art. 156\n\n"
    "§ 1º Os agentes nocivos não arrolados no Anexo IV do RPS, aprovado pelo Decreto "
    "3.048/1999, não serão considerados para fins de concessão da aposentadoria especial.\n"
    "§ 2º As atividades constantes no Anexo IV do RPS, aprovado pelo Decreto 3.048/1999, "
    "são exemplificativas, salvo para agentes biológicos.\n\n"
    "Art. 157\n\n"
    "O núcleo da hipótese de incidência tributária, objeto do direito à aposentadoria "
    "especial, é composto de:\n\n"
    "Nocividade, que no ambiente de trabalho é entendida como situação combinada ou não "
    "de substâncias, energias e demais fatores de risco reconhecidos, capazes de trazer "
    "ou ocasionar danos a saúde ou à integridade física do trabalhador;\n\n"
    "Permanência, assim entendida como trabalho não ocasional nem intermitente, durante "
    "quinze (15), vinte (20) ou vinte e cinco (25) anos, no qual a exposição do empregado, "
    "do trabalhador avulso ou do cooperado ao agente nocivo seja indissociável da produção "
    "do bem ou da prestação do serviço, em decorrência da subordinação jurídica a qual se "
    "submete.\n\n"
    "§ 1º Para apuração do dispositivo no inciso I, há que se considerar se o agente "
    "nocivo é:\n\n"
    "Qualitativo, quando a nocividade é presumida, e independente de mensuração constatado "
    "pela simples presença do agente no ambiente de trabalho, conforme constante nos Anexos "
    "6, 13, 13-A e 14 da Norma Regulamentadora (NR-15) do Ministério do Trabalho e Emprego "
    "- MTE, e no Anexo IV do RPS, aprovado pelo Decreto 3.048/1999, para os agentes iodo e "
    "níquel;\n\n"
    "Quantitativo, quando a nocividade é considerada pela ultrapassagem dos limites de "
    "tolerância ou doses, dispostos nos Anexos 1, 2, 3, 5, 8, 11 e 12 da NR-15 do MTE, "
    "por meio da mensuração da intensidade ou da concentração, consideradas no tempo "
    "efetivo da exposição no ambiente de trabalho.\n\n"
    "§ 2º Quanto ao disposto no inciso II, não quebra a permanência o exercício de função "
    "de supervisão, controle ou comando em geral ou outra atividade equivalente, desde que "
    "seja exclusivamente em ambientes de trabalho cuja nocividade tenha sido constatada."
)


# =============================================================================
# SEÇÃO 5 — PPP
# =============================================================================

PPP_FINALIDADE = (
    "O PPP constitui-se em um documento histórico laboral do trabalhador que reúne, "
    "entre outras informações, dados administrativos, registros ambientais e resultados "
    "de monitoramento biológico, durante todo o período em que este exerceu suas "
    "atividades.\n\n"
    "O PPP TEM COMO FINALIDADE:\n\n"
    "• Comprovar as condições para habilitação de benefícios e serviços previdenciários, "
    "em especial;\n"
    "• Prover o trabalhador de meios de prova produzidos pelo empregador perante a "
    "Previdência Social, a outros órgãos públicos e aos sindicatos, de forma a garantir "
    "todo direito decorrente da relação de trabalho, seja ele individual, ou difuso e "
    "coletivo;\n"
    "• Prover a empresa de meios de prova produzidos em tempo real, de modo a organizar "
    "e a individualizar as informações contidas em seus diversos setores ao longo dos "
    "anos, possibilitando que a empresa evite ações judiciais indevidas relativas a seus "
    "trabalhadores;\n"
    "• Possibilitar aos administradores públicos e privados acessos a bases de informações "
    "fidedignas, como fonte primária de informação estatística, bem como definição de "
    "políticas em saúde coletiva.\n\n"
    "O PPP substitui o formulário para comprovação da efetiva exposição dos segurados "
    "aos agentes nocivos para fins de requerimento da aposentadoria especial, a partir "
    "de 1º de janeiro de 2004, conforme determinado pelo parágrafo 2º do art. 68 do RPS, "
    "aprovado pelo Decreto 3.048/1999 e alterado pelo Decreto 4.032, de 2001."
)

PPP_IMPRESSAO = (
    "O PPP SERÁ IMPRESSO NAS SEGUINTES CONDIÇÕES:\n\n"
    "• Por ocasião da rescisão do contrato de trabalho ou da desfiliação da cooperativa, "
    "sindicato ou OGMO, em duas vias, com fornecimento de uma das vias para o trabalhador, "
    "mediante recibo;\n"
    "• Para fins de requerimento de reconhecimento de períodos laborados em condições "
    "especiais;\n"
    "• Para fins de análise de benefícios por incapacidade, a partir de 1º de janeiro "
    "de 2004, quando solicitado pelo INSS;\n"
    "• Para simples conferência por parte do trabalhador, pelo menos uma vez ao ano, "
    "quando da avaliação global anual do PGR, até que seja implantado o PPP em meio "
    "magnético pela previdência social."
)

PPP_ESPECIFICACOES = (
    "ESPECIFICAÇÕES DO PPP:\n\n"
    "• O PPP deverá ser assinado por representante legal da empresa, com poderes específicos "
    "outorgados por procuração, contendo a indicação dos responsáveis técnicos legalmente "
    "habilitados, por período, pelos registros ambientais e resultados de monitoração "
    "biológica;\n"
    "• A comprovação da entrega do PPP, na rescisão de contrato de trabalho ou da "
    "desfiliação da cooperativa, sindicato ou OGMO, poderá ser feito no próprio instrumento "
    "de rescisão ou de desfiliação, bem como em recibo à parte;\n"
    "• O PPP e a comprovação de entrega ao trabalhador, na rescisão de contrato de trabalho "
    "ou da desfiliação da cooperativa, sindicato ou OGMO, deverão ser mantidos na empresa "
    "por vinte anos;\n"
    "• A prestação de informações falsas no PPP constitui crime de falsidade ideológica, "
    "nos termos do art. 297 do Código Penal. As informações constantes no PPP são de "
    "caráter privativo do trabalhador, constituindo crime nos termos da Lei 9.029, de "
    "13 de abril de 1995, práticas discriminatórias decorrentes de sua exigibilidade "
    "por outrem, bem como de sua divulgação para terceiros, ressalvado quando exigida "
    "pelos órgãos públicos competentes.\n"
    "• O PPP substitui o formulário para comprovação da efetiva exposição dos segurados "
    "aos agentes nocivos para fins de requerimento da aposentadoria especial, a partir "
    "de 1º de janeiro de 2004, conforme determinado pelo parágrafo 2º do art. 68 do RPS, "
    "aprovado pelo Decreto 3.048/1999 e alterado pelo Decreto 4.032, de 2001."
)


# =============================================================================
# SEÇÃO 8 — AVALIAÇÃO DE PERICULOSIDADE
# =============================================================================

PERICULOSIDADE_EXPLOSIVOS = (
    "PERICULOSIDADE EM RAZÃO DE EXPLOSIVOS - (NR-16, ANEXO 01).\n\n"
    "As funções avaliadas não lidam com iniciadores, artefatos e substâncias explosivas "
    "e não trabalham em área de risco normatizada."
)

PERICULOSIDADE_INFLAMAVEIS = (
    "PERICULOSIDADE EM RAZÃO DE INFLAMÁVEIS - (NR-16, ANEXO 02). "
    "DA NORMA REGULAMENTADORA - NR-16 E SEUS ANEXOS:\n\n"
    "As funções avaliadas não lidam com iniciadores, razão de Inflamáveis "
    "e não trabalham em área de risco normatizada."
)

PERICULOSIDADE_VIOLENCIA = (
    "ATIVIDADES E OPERAÇÕES PERIGOSAS COM EXPOSIÇÃO A ROUBOS OU OUTRAS ESPÉCIES DE "
    "VIOLÊNCIA FÍSICA NAS ATIVIDADES PROFISSIONAIS DE SEGURANÇA PESSOAL OU PATRIMONIAL "
    "- (NR-16, ANEXOS 03)\n\n"
    "As funções avaliadas não lidam com Exposição a roubos ou outras espécies de violência "
    "física nas atividades profissionais e não trabalham em área de risco normatizada."
)

PERICULOSIDADE_ELETRICIDADE = (
    "PERICULOSIDADE EM RAZÃO DE ELETRICIDADE – (NR 16 ANEXO 04)\n\n"
    "{texto_periculosidade_eletricidade}"
)

PERICULOSIDADE_TRANSITO = (
    "ATIVIDADES PERIGOSAS DOS AGENTES DAS AUTORIDADES DE TRÂNSITO – (NR 16 ANEXO 06)\n\n"
    "As funções avaliadas não lidam com agente de trânsito "
    "e não trabalham em área de risco normatizada."
)

PERICULOSIDADE_RADIACAO = (
    "ATIVIDADES E OPERAÇÕES PERIGOSAS COM RADIAÇÕES IONIZANTES OU SUBSTÂNCIAS "
    "RADIOATIVAS – (NR 16)\n\n"
    "As funções avaliadas não lidam com Radiações ionizantes ou substâncias radioativas "
    "e não trabalham em área de risco normatizada."
)

PERICULOSIDADE_CONCLUSAO = (
    "Em análises das atividades e nos critérios estabelecidos na Norma Regulamentadora "
    "nº 16 (NR-16) da Portaria nº 3.214/78 do Ministério do Trabalho — "
    "Ausência de Risco Específico."
)


# =============================================================================
# SEÇÃO 11 — EMBASAMENTO LEGAL
# =============================================================================

EMBASAMENTO_RUIDO_INTRO = (
    "11.1 - AGENTE FÍSICO RUÍDO - NR-15, ANEXO 1\n\n"
    '"São considerados insalubres em grau médio os trabalhos realizados com exposição '
    "a níveis de ruídos acima dos limites de tolerância estabelecidos, sem o uso de "
    'EPI – Equipamento de Proteção adequado."'
)

EMBASAMENTO_DEMAIS_INTRO = (
    "11.2 - DEMAIS AGENTES INSALUBRES\n\n"
    "O limite de tolerância e graus de insalubridade dos demais agentes, são baseados "
    "conforme estabelece a NR 15 e seus anexos, conforme a lista abaixo:"
)


# =============================================================================
# SEÇÃO 12 — REFERÊNCIAS BIBLIOGRÁFICAS
# =============================================================================

REFERENCIAS_BIBLIOGRAFICAS = (
    "• Legislação de Segurança e Medicina do Trabalho, Lei N° 6514/77 que regulamentou "
    "a Portaria N° 3.214/78, do Ministério do Trabalho e Emprego.\n\n"
    "• Lei n° 8213/91 e alterações de seu texto pelas Leis n° 9.032/95, 9528/97 e "
    "9732/98.\n\n"
    "• Decretos regulamentadores da Previdência Social: Dec. 53831/64, Dec. 83080/79, "
    "Dec. 2172/97, Dec. 3048/99 e Dec. 4032/01. Instruções Normativas do INSS: IN "
    "INSS/DC n° 57 de 10.10.2001, IN INSS/DC n° 78 de 16.07.2002\n\n"
    "• Manual de Engenharia Química, Perry and Chilton.\n\n"
    "• Normas de Higiene do Trabalho da Fundacentro, NHO 01 Norma de Higiene "
    "Ocupacional de Ruído."
)


# =============================================================================
# SEÇÃO 13 — RESPONSÁVEL TÉCNICO (encerramento)
# =============================================================================

RESPONSAVEL_TECNICO = (
    "O profissional abaixo assinado é o responsável técnico pela elaboração deste laudo, "
    "cabendo à empresa a responsabilidade pela implementação."
)


# =============================================================================
# TABELA NR-15 ANEXO 1 — DADOS
# =============================================================================

TABELA_RUIDO_NR15 = [
    ('85', '8 horas'),
    ('86', '7 horas'),
    ('87', '6 horas'),
    ('88', '5 horas'),
    ('89', '4 horas e 30 minutos'),
    ('90', '4 horas'),
    ('91', '3 horas e 30 minutos'),
    ('92', '3 horas'),
    ('93', '2 horas e 40 minutos'),
    ('94', '2 horas e 15 minutos'),
    ('95', '2 horas'),
    ('96', '1 hora e 45 minutos'),
    ('98', '1 hora e 15 minutos'),
    ('100', '1 hora'),
    ('102', '45 minutos'),
    ('104', '35 minutos'),
    ('105', '30 minutos'),
    ('106', '25 minutos'),
    ('108', '20 minutos'),
    ('110', '15 minutos'),
    ('112', '10 minutos'),
    ('114', '8 minutos'),
    ('115', '7 minutos'),
]

TABELA_DEMAIS_AGENTES = [
    ('Calor', 'NR 15 – Anexo 3'),
    ('Radiações Ionizantes', 'NR 15 – Anexo 5'),
    ('Condições Hiperbáricas', 'NR 15 – Anexo 6'),
    ('Radiações Não Ionizantes', 'NR 15 – Anexo 7'),
    ('Vibrações', 'NR 15 – Anexo 8'),
    ('Frio', 'NR 15 – Anexo 9'),
    ('Umidade', 'NR 15 – Anexo 10'),
    ('Agentes Químicos – Por limite de Exposição', 'NR 15 – Anexo 11'),
    ('Agentes Químicos – Poeiras Minerais', 'NR 15 – Anexo 12'),
    ('Agentes Químicos – Qualitativo', 'NR 15 – Anexo 13'),
    ('Agentes Químicos – Benzeno e seus Compostos', 'NR 15 – Anexo 13A'),
    ('Agentes Biológicos', 'NR 15 – Anexo 14'),
]


# =============================================================================
# DICIONÁRIO CENTRAL
# =============================================================================

TEXTOS_LTCAT = {
    'objetivo': OBJETIVO,
    'condicoes_preliminares': CONDICOES_PRELIMINARES,
    'codigos_gfip': CODIGOS_GFIP,
    'trabalho_permanente': TRABALHO_PERMANENTE,
    'agentes_nocivos': AGENTES_NOCIVOS,
    'ppp_finalidade': PPP_FINALIDADE,
    'ppp_impressao': PPP_IMPRESSAO,
    'ppp_especificacoes': PPP_ESPECIFICACOES,
    'periculosidade_explosivos': PERICULOSIDADE_EXPLOSIVOS,
    'periculosidade_inflamaveis': PERICULOSIDADE_INFLAMAVEIS,
    'periculosidade_violencia': PERICULOSIDADE_VIOLENCIA,
    'periculosidade_eletricidade': PERICULOSIDADE_ELETRICIDADE,
    'periculosidade_transito': PERICULOSIDADE_TRANSITO,
    'periculosidade_radiacao': PERICULOSIDADE_RADIACAO,
    'periculosidade_conclusao': PERICULOSIDADE_CONCLUSAO,
    'embasamento_ruido_intro': EMBASAMENTO_RUIDO_INTRO,
    'embasamento_demais_intro': EMBASAMENTO_DEMAIS_INTRO,
    'referencias_bibliograficas': REFERENCIAS_BIBLIOGRAFICAS,
    'responsavel_tecnico': RESPONSAVEL_TECNICO,
}


def get_texto(chave, **kwargs):
    """Retorna texto padrão com substituição de variáveis."""
    texto = TEXTOS_LTCAT.get(chave, '')
    if kwargs:
        try:
            texto = texto.format(**kwargs)
        except KeyError:
            pass
    return texto


