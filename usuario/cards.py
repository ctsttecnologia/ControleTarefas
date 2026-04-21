
# usuario/cards.py
"""
Definição centralizada dos cards do dashboard do usuário.
Separado da view para facilitar manutenção e testes.
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
        ]
    },
    {
        'id': 'dp',
        'title': 'Departamento Pessoal',
        'permission': 'departamento_pessoal.view_painel_dp',
        'icon': 'images/dp.gif',
        'links': [
            {'url': 'departamento_pessoal:painel_dp', 'text': 'Painel DP',
             'permission': 'departamento_pessoal.view_funcionario'},
            {'url': 'treinamentos:dashboard', 'text': 'Treinamentos'},
        ]
    },
    {
        'id': 'sst',
        'title': 'Segurança do Trabalho',
        'permission': 'seguranca_trabalho.view_fichaepi',
        'icon': 'images/tst.gif',
        'links': [
            {'url': 'seguranca_trabalho:dashboard', 'text': 'Painel SST', 'permission': 'seguranca_trabalho.view_fichaepi'},
            {'url': 'seguranca_trabalho:ficha_list', 'text': 'Fichas de EPI', 'permission': 'seguranca_trabalho.view_fichaepi'},
            {'url': 'gestao_riscos:lista_riscos', 'text': 'Gestão de Riscos', 'permission': 'gestao_riscos.view_risco'},
        ]
    },
    {
        'id': 'endereco',
        'title': 'Logradouro',
        'permission': 'logradouro.view_logradouro',
        'icon': 'images/cadastro.gif',
        'links': [
            {'url': 'logradouro:cadastrar_logradouro', 'text': 'Cadastrar', 'permission': 'logradouro.add_logradouro'},
            {'url': 'logradouro:listar_logradouros', 'text': 'Lista de Logradouros', 'permission': 'logradouro.view_logradouro'},
        ]
    },
    {
        'id': 'ata_reuniao',
        'title': 'Atas de Reunião',
        'permission': 'ata_reuniao.view_atareuniao',
        'icon': 'images/reuniao.png',
        'links': [
            {'url': 'ata_reuniao:ata_reuniao_dashboard', 'text': 'Painel de Atas', 'permission': 'ata_reuniao.view_atareuniao'},
            {'url': 'ata_reuniao:ata_reuniao_list', 'text': 'Lista de Atas', 'permission': 'ata_reuniao.view_atareuniao'},
        ]
    },
    {
        'id': 'suprimentos',
        'title': 'Suprimentos',
        'permission': 'suprimentos.view_pedido',
        'icon': 'images/suprimentos.gif',
        'links': [
            {'url': 'suprimentos:dashboard', 'text': 'Suprimentos', 'permission': 'suprimentos.view_pedido'},
        ]
    },
    {
        'id': 'documentos',
        'title': 'Documentos',
        'permission': 'documentos.view_documento',
        'icon': 'images/documentos.gif',
        'links': [
            {'url': 'documentos:lista', 'text': 'Gestão de Documentos', 'permission': 'documentos.view_documento'},
        ]
    },
    {
        'id': 'telefones',
        'title': 'Controle de Telefones',
        'permission': 'controle_de_telefone.view_linhatelefonica',
        'icon': 'images/telefones.gif',
        'links': [
            {'url': 'controle_de_telefone:dashboard', 'text': 'Gestão de Telefones', 'permission': 'controle_de_telefone.view_linhatelefonica'},
        ]
    },
    {
        'id': 'estoque',
        'title': 'Estoque',
        'permission': 'seguranca_trabalho.view_equipamento',
        'icon': 'images/estoque.gif',
        'links': [
            {'url': 'seguranca_trabalho:equipamento_list', 'text': 'Equipamentos e Material', 'permission': 'seguranca_trabalho.view_equipamento'},
        ]
    },
    {
        'id': 'veiculos',
        'title': 'Veículos',
        'permission': 'automovel.view_carro',
        'icon': 'images/carro.gif',
        'links': [
            {'url': 'automovel:carro_list', 'text': 'Frota', 'permission': 'automovel.view_carro'},
            {'url': 'automovel:agendamento_list', 'text': 'Agendamentos', 'permission': 'automovel.view_agendamento'},
            {'url': 'automovel:dashboard', 'text': 'Relatórios', 'permission': 'automovel.view_dashboard'},
        ]
    },
    {
        'id': 'operacao',
        'title': 'Operação',
        'permission': 'ferramentas.view_ferramentas',
        'icon': 'images/serviço.gif',
        'links': [
            {'url': 'tarefas:dashboard', 'text': 'Tarefas', 'permission': 'tarefas.view_dashboard'},
            {'url': 'ferramentas:dashboard', 'text': 'Ferramentas', 'permission': 'ferramentas.view_dashboard'},
        ]
    },
    {
        'id': 'main_dashboard',
        'title': 'Dashboard Integrado',
        'permission': 'GARANT_ALL',
        'icon': 'images/favicon.ico',
        'links': [
            {'url': 'dashboard:dashboard_geral', 'text': 'Visão Geral', 'permission': 'dashboard.view_dashboard_geral'},
        ]
    },
]


# IDs utilizados na tela de gerenciamento de permissões
CARD_SUMMARY = [
    {'id': c['id'], 'title': c['title']} for c in ALL_CARDS
]


def get_all_cards():
    """Retorna lista completa de cards."""
    return ALL_CARDS


def get_card_ids():
    """Retorna apenas os IDs dos cards (útil para validação)."""
    return {c['id'] for c in ALL_CARDS}

