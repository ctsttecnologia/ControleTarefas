

# notifications/signals.py

"""
Signals que geram notificações automaticamente
a partir de eventos em outros módulos.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from tarefas.models import HistoricoStatus
from .services import notificar_tarefa_status


# =============================================================================
# SIGNAL: Mudança de status de tarefa → Notificação
# =============================================================================
@receiver(post_save, sender=HistoricoStatus)
def gerar_notificacao_mudanca_status(sender, instance, created, **kwargs):
    """Gera notificação quando o status de uma tarefa muda."""
    if not created:
        return

    tarefa = instance.tarefa
    alterado_por = instance.alterado_por if hasattr(instance, 'alterado_por') else None

    notificar_tarefa_status(
        tarefa=tarefa,
        status_anterior=instance.status_anterior,
        novo_status=instance.novo_status,
        alterado_por=alterado_por,
    )
