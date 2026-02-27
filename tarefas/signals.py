

# tarefas/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import HistoricoStatus
from .utils import enviar_email_tarefa


@receiver(post_save, sender=HistoricoStatus)
def notificar_mudanca_status(sender, instance, created, **kwargs):
    """Dispara e-mail quando o status de uma tarefa muda."""
    if not created:
        return

    tarefa = instance.tarefa

    destinatarios = set()
    if tarefa.usuario and tarefa.usuario.email:
        destinatarios.add(tarefa.usuario.email)
    if tarefa.responsavel and tarefa.responsavel.email:
        destinatarios.add(tarefa.responsavel.email)

    if not destinatarios:
        return

    contexto = {
        'tarefa': tarefa,
        'status_anterior': instance.get_status_anterior_display()
            if hasattr(instance, 'get_status_anterior_display')
            else instance.status_anterior,
        'novo_status': instance.get_novo_status_display()
            if hasattr(instance, 'get_novo_status_display')
            else instance.novo_status,
        'alterado_por': instance.alterado_por,
    }

    enviar_email_tarefa(
        assunto=f"Status da tarefa '{tarefa.titulo}' alterado",
        template_texto='tarefas/emails/email_notificacao_status.txt',
        template_html='tarefas/emails/email_notificacao_status.html',
        contexto=contexto,
        destinatarios=list(destinatarios),
    )

