# notifications/signals.py — SUBSTITUIR completamente

"""
Signals que geram notificações automaticamente.
- HistoricoTarefa (status) → Notificação sino + E-mail
- M2M participantes → Histórico + Notificação + E-mail
"""

import logging

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from tarefas.models import HistoricoTarefa, Tarefas

logger = logging.getLogger(__name__)


# =============================================================================
# SIGNAL: HistoricoTarefa criado (tipo=status) → Notificação + E-mail
# =============================================================================

@receiver(post_save, sender=HistoricoTarefa)
def gerar_notificacao_historico(sender, instance, created, **kwargs):
    """Quando um HistoricoTarefa de tipo 'status' é criado, notifica todos."""
    if not created:
        return

    # Só status gera notificação (participante é tratado no m2m signal)
    if instance.tipo_alteracao != 'status':
        return

    from .services import notificar_tarefa_status_participantes

    try:
        notificar_tarefa_status_participantes(
            tarefa=instance.tarefa,
            status_anterior=instance.valor_anterior,
            novo_status=instance.valor_novo,
            alterado_por=instance.alterado_por,
        )
    except Exception as e:
        logger.error(
            f'Erro ao notificar status da tarefa {instance.tarefa_id}: {e}',
            exc_info=True,
        )


# =============================================================================
# SIGNAL: Participantes M2M → Histórico + Notificação + E-mail
# =============================================================================

@receiver(m2m_changed, sender=Tarefas.participantes.through)
def registrar_e_notificar_participantes(sender, instance, action, pk_set, **kwargs):
    """
    Quando participantes são adicionados ou removidos:
    1. Registra no histórico (HistoricoTarefa)
    2. Notifica os novos participantes (sino + e-mail)
    """
    if action not in ('post_add', 'post_remove') or not pk_set:
        return

    from django.contrib.auth import get_user_model
    from tarefas.services import registrar_alteracao_participantes
    from .services import notificar_tarefa_participante_adicionado

    User = get_user_model()
    tarefa = instance
    alterado_por = getattr(tarefa, '_user', None)
    usuarios = User.objects.filter(pk__in=pk_set)

    # ── 1. Registrar no Histórico ──
    acao = 'add' if action == 'post_add' else 'remove'
    try:
        registrar_alteracao_participantes(
            tarefa=tarefa,
            usuarios=usuarios,
            acao=acao,
            alterado_por=alterado_por,
        )
    except Exception as e:
        logger.error(
            f'Erro ao registrar histórico participantes tarefa {tarefa.pk}: {e}',
            exc_info=True,
        )

    # ── 2. Notificar novos participantes (apenas adição) ──
    if action == 'post_add':
        try:
            notificar_tarefa_participante_adicionado(
                tarefa=tarefa,
                novos_participantes=usuarios,
                adicionado_por=alterado_por,
            )
        except Exception as e:
            logger.error(
                f'Erro ao notificar participantes tarefa {tarefa.pk}: {e}',
                exc_info=True,
            )


