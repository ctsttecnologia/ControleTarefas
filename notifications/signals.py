
# notifications/signals.py

"""
Signals que geram notificações automaticamente
a partir de eventos em outros módulos.

Centraliza:
- Notificações no sistema (sino)
- Envio de e-mails
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from tarefas.models import HistoricoStatus
from .services import notificar_tarefa_status, enviar_email


# =============================================================================
# SIGNAL: Mudança de status de tarefa → Notificação + E-mail
# =============================================================================

@receiver(post_save, sender=HistoricoStatus)
def gerar_notificacao_mudanca_status(sender, instance, created, **kwargs):
    """
    Quando o status de uma tarefa muda:
    1. Cria notificação no sistema (sino) via notificar_tarefa_status
    2. Envia e-mail para responsável e criador
    """
    if not created:
        return

    tarefa = instance.tarefa
    alterado_por = instance.alterado_por if hasattr(instance, 'alterado_por') else None

    status_anterior = (
        instance.get_status_anterior_display()
        if hasattr(instance, 'get_status_anterior_display')
        else instance.status_anterior
    )
    novo_status = (
        instance.get_novo_status_display()
        if hasattr(instance, 'get_novo_status_display')
        else instance.novo_status
    )

    # ─── 1. Notificação no sistema (sino) ───
    notificar_tarefa_status(
        tarefa=tarefa,
        status_anterior=status_anterior,
        novo_status=novo_status,
        alterado_por=alterado_por,
    )

    # ─── 2. Envio de e-mail ───
    destinatarios = set()
    if tarefa.usuario and tarefa.usuario.email:
        destinatarios.add(tarefa.usuario.email)
    if tarefa.responsavel and tarefa.responsavel.email:
        destinatarios.add(tarefa.responsavel.email)

    if not destinatarios:
        return

    contexto = {
        'tarefa': tarefa,
        'status_anterior': status_anterior,
        'novo_status': novo_status,
        'alterado_por': alterado_por,
    }

    enviar_email(
        assunto=f"Status da tarefa '{tarefa.titulo}' alterado",
        template_texto='tarefas/emails/email_notificacao_status.txt',
        template_html='tarefas/emails/email_notificacao_status.html',
        contexto=contexto,
        destinatarios=list(destinatarios),
    )

