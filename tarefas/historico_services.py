
# tarefas/historico_services.py — NOVO ARQUIVO (separado do services.py existente)

"""
Serviço centralizado para registro de histórico de tarefas.
Rastreia QUALQUER alteração feita em uma tarefa.
"""

import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Campos rastreados automaticamente e como formatá-los
# ═══════════════════════════════════════════════════════════════════════

CAMPOS_RASTREADOS = {
    'titulo': {
        'label': 'Título',
        'tipo': 'titulo',
    },
    'descricao': {
        'label': 'Descrição',
        'tipo': 'descricao',
    },
    'status': {
        'label': 'Status',
        'tipo': 'status',
        'use_display': True,
    },
    'prioridade': {
        'label': 'Prioridade',
        'tipo': 'prioridade',
        'use_display': True,
    },
    'responsavel': {
        'label': 'Responsável',
        'tipo': 'responsavel',
        'is_fk': True,
    },
    'prazo': {
        'label': 'Prazo',
        'tipo': 'prazo',
        'is_date': True,
    },
    'data_inicio': {
        'label': 'Data de Início',
        'tipo': 'geral',
        'is_date': True,
    },
    'projeto': {
        'label': 'Projeto',
        'tipo': 'projeto',
    },
    'duracao_prevista': {
        'label': 'Duração Prevista',
        'tipo': 'geral',
    },
    'tempo_gasto': {
        'label': 'Tempo Gasto',
        'tipo': 'geral',
    },
    'dias_lembrete': {
        'label': 'Dias p/ Lembrete',
        'tipo': 'geral',
    },
    'recorrente': {
        'label': 'Recorrente',
        'tipo': 'recorrencia',
        'is_bool': True,
    },
    'frequencia_recorrencia': {
        'label': 'Frequência',
        'tipo': 'recorrencia',
        'use_display': True,
    },
    'data_fim_recorrencia': {
        'label': 'Fim da Recorrência',
        'tipo': 'recorrencia',
        'is_date': True,
    },
}


def _formatar_valor(obj_ref, campo, valor, config):
    """Formata um valor para exibição legível no histórico."""
    if valor is None or valor == '':
        return 'Não definido'

    if config.get('is_bool'):
        return 'Sim' if valor else 'Não'

    if config.get('use_display'):
        display_method = getattr(obj_ref, f'get_{campo}_display', None)
        if display_method:
            try:
                return display_method()
            except Exception:
                pass

    if config.get('is_fk'):
        if hasattr(valor, 'get_full_name'):
            return valor.get_full_name() or str(valor)
        return str(valor) if valor else 'Não atribuído'

    if config.get('is_date'):
        if hasattr(valor, 'strftime'):
            return valor.strftime('%d/%m/%Y %H:%M')
        return str(valor)

    return str(valor)


# ═══════════════════════════════════════════════════════════════════════
# FUNÇÕES PRINCIPAIS
# ═══════════════════════════════════════════════════════════════════════

def registrar_criacao_tarefa(tarefa, usuario):
    """Registra a criação de uma nova tarefa no histórico."""
    from .models import HistoricoTarefa

    try:
        HistoricoTarefa.objects.create(
            tarefa=tarefa,
            alterado_por=usuario,
            tipo_alteracao='criacao',
            campo_alterado='',
            valor_anterior='',
            valor_novo='',
            descricao='Tarefa criada',
            filial=tarefa.filial,
        )
    except Exception as e:
        logger.error(f'Erro ao registrar criação da tarefa {tarefa.pk}: {e}')


def registrar_alteracoes_tarefa(tarefa, usuario):
    """
    Compara o estado atual da tarefa (em memória) com o estado no banco
    e registra TODAS as diferenças no histórico.

    ⚠️ Deve ser chamado ANTES do super().save()
    """
    from .models import HistoricoTarefa, Tarefas

    if not tarefa.pk:
        return []

    try:
        antiga = Tarefas.objects.select_related('responsavel').get(pk=tarefa.pk)
    except Tarefas.DoesNotExist:
        return []

    registros = []

    for campo, config in CAMPOS_RASTREADOS.items():
        # Pular campo 'status' — já tratado separadamente no save()
        if campo == 'status':
            continue

        valor_antigo = getattr(antiga, campo, None)
        valor_novo = getattr(tarefa, campo, None)

        # Normalizar para comparação
        if config.get('is_fk'):
            antigo_pk = valor_antigo.pk if valor_antigo else None
            novo_pk = None
            if hasattr(valor_novo, 'pk'):
                novo_pk = valor_novo.pk
            elif isinstance(valor_novo, int):
                novo_pk = valor_novo
            elif valor_novo is None:
                novo_pk = None
            mudou = antigo_pk != novo_pk
        elif config.get('is_date'):
            mudou = str(valor_antigo or '') != str(valor_novo or '')
        elif config.get('is_bool'):
            mudou = bool(valor_antigo) != bool(valor_novo)
        else:
            mudou = str(valor_antigo or '') != str(valor_novo or '')

        if not mudou:
            continue

        antigo_display = _formatar_valor(antiga, campo, valor_antigo, config)
        novo_display = _formatar_valor(tarefa, campo, valor_novo, config)

        label = config['label']

        # Descrição legível
        if config.get('tipo') == 'descricao':
            desc = f'{label} atualizada'
        elif config.get('tipo') == 'titulo':
            desc = f'{label}: "{antigo_display}" → "{novo_display}"'
        else:
            desc = f'{label}: {antigo_display} → {novo_display}'

        try:
            h = HistoricoTarefa.objects.create(
                tarefa=tarefa,
                alterado_por=usuario,
                tipo_alteracao=config['tipo'],
                campo_alterado=campo,
                valor_anterior=str(antigo_display),
                valor_novo=str(novo_display),
                descricao=desc,
                filial=tarefa.filial,
            )
            registros.append(h)
        except Exception as e:
            logger.error(
                f'Erro ao registrar alteração [{campo}] tarefa {tarefa.pk}: {e}'
            )

    return registros


def registrar_alteracao_status(tarefa, status_anterior_key, novo_status_key, alterado_por=None):
    """
    Registra mudança de status no histórico.
    Chamado pelo save() do model e pelas views AJAX.
    """
    from .models import HistoricoTarefa, Tarefas

    status_dict = dict(Tarefas.STATUS_CHOICES)
    anterior_display = status_dict.get(status_anterior_key, status_anterior_key)
    novo_display = status_dict.get(novo_status_key, novo_status_key)

    try:
        return HistoricoTarefa.objects.create(
            tarefa=tarefa,
            alterado_por=alterado_por,
            tipo_alteracao='status',
            campo_alterado='status',
            valor_anterior=anterior_display,
            valor_novo=novo_display,
            descricao=f'Status: {anterior_display} → {novo_display}',
            filial=tarefa.filial,
        )
    except Exception as e:
        logger.error(f'Erro ao registrar status da tarefa {tarefa.pk}: {e}')
        return None


def registrar_alteracao_participantes(tarefa, usuarios, acao, alterado_por=None):
    """
    Registra adição ou remoção de participantes no histórico.
    acao: 'add' ou 'remove'
    """
    from .models import HistoricoTarefa

    nomes = [u.get_full_name() or u.username for u in usuarios]
    nomes_str = ', '.join(nomes)

    if acao == 'add':
        tipo = 'participante_add'
        desc = f'Participante(s) adicionado(s): {nomes_str}'
    else:
        tipo = 'participante_remove'
        desc = f'Participante(s) removido(s): {nomes_str}'

    try:
        return HistoricoTarefa.objects.create(
            tarefa=tarefa,
            alterado_por=alterado_por,
            tipo_alteracao=tipo,
            campo_alterado='participantes',
            valor_anterior='' if acao == 'add' else nomes_str,
            valor_novo=nomes_str if acao == 'add' else '',
            descricao=desc,
            filial=tarefa.filial,
        )
    except Exception as e:
        logger.error(f'Erro ao registrar participantes da tarefa {tarefa.pk}: {e}')
        return None

