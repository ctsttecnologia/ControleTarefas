
# pgr_gestao/constants.py
# RASCUNHO: revisar textos, públicos, periodicidades e responsáveis com o SESMT.
# Formato: (numero_item, acao_necessaria, publico_alvo, periodicidade, responsavel)
# 'periodicidade' deve ser um valor de PERIODICIDADE_CHOICES (models.py ~linha 150).

ACOES_PADRAO = [
    (1, "Revisão geral do PGR e do inventário de riscos ocupacionais.",
     "Todos os GES", "anual", "SESMT / Responsável Técnico"),
    (2, "Reavaliação dos riscos após mudanças de processo, layout, máquinas, "
        "produtos químicos ou métodos de trabalho.",
     "GES e setores afetados", "anual", "SESMT / Gestores de área"),
    (3, "Realização e atualização das avaliações quantitativas dos agentes "
        "(ruído, calor, agentes químicos, vibração, etc.).",
     "GES expostos aos agentes", "anual", "Higienista / Técnico de Segurança"),
    (4, "Treinamentos de segurança e saúde no trabalho, incluindo integração "
        "de novos colaboradores e reciclagens.",
     "Todos os trabalhadores", "anual", "SESMT / RH"),
    (5, "Diálogo Diário/Mensal de Segurança (DDS) sobre os riscos da atividade.",
     "Todos os trabalhadores", "mensal", "Supervisores / Técnico de Segurança"),
    (6, "Inspeções de segurança nos ambientes e postos de trabalho.",
     "Ambientes de trabalho", "trimestral", "Técnico de Segurança / CIPA"),
    (7, "Verificação do uso, estado de conservação, validade e CA dos EPIs; "
        "reposição quando necessário.",
     "Usuários de EPI", "semestral", "Técnico de Segurança / Almoxarifado"),
    (8, "Acompanhamento da execução e dos prazos do plano de ação.",
     "Responsáveis pelas ações", "trimestral", "SESMT / Gestão"),
    (9, "Análise de acidentes, incidentes e quase-acidentes, com definição "
        "de ações corretivas.",
     "Todos os trabalhadores", "mensal", "SESMT / CIPA"),
    (10, "Verificação da eficácia das medidas de controle e integração dos "
         "resultados com o PCMSO.",
     "Todos os GES", "anual", "SESMT / Médico do Trabalho"),
]

