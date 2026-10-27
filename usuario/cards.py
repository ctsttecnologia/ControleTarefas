
# usuario/cards.py
"""
Definição centralizada dos cards do dashboard do usuário.
`permission` do card aceita str ou lista (basta UMA para liberar).
"""

ALL_CARDS = [
    {
        'id': 'clientes',
        'title': 'Clientes',
        'permission': 'cliente.view_cliente',
        'icon': 'images/cliente.gif',
        'links': [
            {'url': 'cliente:cliente_create', 'text': 'Cadastrar', 'permission': 'cliente.add_cliente'},
            {'url': 'cliente:lista_clientes', 'text': 'Lista de Clientes', 'permission': 'cliente.view_cliente'},
        ],
    },
    {
        'id': 'dp',
        'title': 'Departamento Pessoal',
        'permission': ['departamento_pessoal.view_funcionario', 'treinamentos.view_treinamento'],
        'icon': 'images/dp.gif',
        'links': [
            {'url': 'departamento_pessoal:painel_dp', 'text': 'Painel', 'permission': 'departamento_pessoal.view_funcionario'},
            {'url': 'treinamentos:dashboard', 'text': 'Treinamentos', 'permission': 'treinamentos.view_treinamento'},
        ],
        },
            {
            'id': 'sst',
            'title': 'Segurança do Trabalho',
            'permission': [
                'seguranca_trabalho.view_fichaepi',
                'gestao_riscos.view_tiporisco',
                'gestao_riscos.view_incidente',
                'gestao_riscos.view_inspecao',
                'gestao_riscos.view_cartaotag',
            ],
            'icon': 'images/tst.gif',
            'links': [
                {'url': 'seguranca_trabalho:dashboard', 'text': 'Painel', 'permission': 'seguranca_trabalho.view_fichaepi'},
                {'url': 'seguranca_trabalho:acesso_rapido', 'text': 'Acesso Rápido', 'permission': 'seguranca_trabalho.view_fichaepi'},
                {'url': 'gestao_riscos:lista_riscos', 'text': 'Gestão de Riscos', 'permission': 'gestao_riscos.view_listariscos'},
            ],
        },

    {
        'id': 'endereco',
        'title': 'Logradouro',
        'permission': 'logradouro.view_logradouro',
        'icon': 'images/cadastro.gif',
        'links': [
            {'url': 'logradouro:cadastrar_logradouro', 'text': 'Cadastrar', 'permission': 'logradouro.add_logradouro'},
            {'url': 'logradouro:listar_logradouros', 'text': 'Lista de Logradouros', 'permission': 'logradouro.view_logradouro'},
        ],
    },
    {
        'id': 'ata_reuniao',
        'title': 'Atas de Reunião',
        'permission': 'ata_reuniao.view_atareuniao',
        'icon': 'images/reuniao.png',
        'links': [
            {'url': 'ata_reuniao:ata_reuniao_dashboard', 'text': 'Painel', 'permission': 'ata_reuniao.view_atareuniao'},
            {'url': 'ata_reuniao:ata_reuniao_list', 'text': 'Lista de Atas', 'permission': 'ata_reuniao.view_atareuniao'},
        ],
    },
    {
        'id': 'suprimentos',
        'title': 'Suprimentos',
        'permission': 'suprimentos.view_pedido',
        'icon': 'images/suprimentos.gif',
        'links': [
            {'url': 'suprimentos:dashboard', 'text': 'Painel', 'permission': 'suprimentos.view_pedido'},
        ],
    },
    {
        'id': 'documentos',
        'title': 'Documentos',
        'permission': 'documentos.view_documento',
        'icon': 'images/documentos.gif',
        'links': [
            {'url': 'documentos:lista', 'text': 'Gestão de Documentos', 'permission': 'documentos.view_documento'},
        ],
    },
    {
        'id': 'estoque',
        'title': 'Estoque',
        'permission': 'seguranca_trabalho.view_equipamento',
        'icon': 'images/estoque.gif',
        'links': [
            {'url': 'seguranca_trabalho:equipamento_list', 'text': 'Equipamentos e Material', 'permission': 'seguranca_trabalho.view_equipamento'},
        ],
    },
    {
        'id': 'veiculos',
        'title': 'Veículos',
        'permission': ['automovel.view_carro', 'automovel.view_carro_agendamento'],
        'icon': 'images/carro.gif',
        'links': [
            {'url': 'automovel:carro_list', 'text': 'Frota', 'permission': 'automovel.view_carro'},
            {'url': 'automovel:agendamento_list', 'text': 'Agendamentos', 'permission': 'automovel.view_carro_agendamento'},
            {'url': 'automovel:dashboard', 'text': 'Relatórios', 'permission': 'automovel.view_carro_agendamento'},
        ],
    },
    {
        'id': 'operacao',
        'title': 'Operação',
        'permission': [
            'tarefas.view_dashboard',
            'ferramentas.view_ferramenta',
            'relatorio_fotografico.view_relatoriofotografico',
        ],
        'icon': 'images/serviço.gif',
        'links': [
            {'url': 'tarefas:dashboard', 'text': 'Tarefas', 'permission': 'tarefas.view_dashboard'},
            {'url': 'ferramentas:dashboard', 'text': 'Ferramentas', 'permission': 'ferramentas.view_ferramenta'},
            {'url': 'relatorio_fotografico:list', 'text': 'Relatórios Fotográficos', 'permission': 'relatorio_fotografico.view_relatoriofotografico'},
        ],
    },

    {
        'id': 'main_dashboard',
        'title': 'Dashboard Integrado',
        'permission': ['usuario.pode_ver_dashboard_geral', 'dashboard.view_dashboard_geral'],
        'icon': 'images/favicon.ico',
        'links': [
            {'url': 'dashboard:dashboard_geral', 'text': 'Visão Geral', 'permission': 'dashboard.view_dashboard_geral'},
        ],
    },
]

CARD_SUMMARY = [{'id': c['id'], 'title': c['title']} for c in ALL_CARDS]


def get_all_cards():
    return ALL_CARDS


def get_card_ids():
    return {c['id'] for c in ALL_CARDS}


def card_perms(card):
    """Normaliza a permissão do card para lista."""
    p = card.get('permission') or []
    return [p] if isinstance(p, str) else list(p)


def all_declared_perms():
    """Todas as permissões citadas (para validação)."""
    perms = set()
    for c in ALL_CARDS:
        perms.update(card_perms(c))
        perms.update(l['permission'] for l in c['links'] if l.get('permission'))
    return perms

