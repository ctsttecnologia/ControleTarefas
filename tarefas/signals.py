from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import HistoricoStatus
from .utils import enviar_email_tarefa

@receiver(post_save, sender=HistoricoStatus)
def notificar_mudanca_status(sender, instance, created, **kwargs):
    """
    Dispara um e-mail quando o status de uma tarefa muda.
    """
    if created:
        tarefa = instance.tarefa
        
        # Define quem deve ser notificado. Vamos avisar o criador E o responsável.
        # O 'set' é usado para evitar enviar o mesmo e-mail duas vezes se o criador for o responsável.
        destinatarios = set()
        if tarefa.usuario and tarefa.usuario.email:
            destinatarios.add(tarefa.usuario.email)
        if tarefa.responsavel and tarefa.responsavel.email:
            destinatarios.add(tarefa.responsavel.email)
        
        # Prepara o contexto para os templates de e-mail
        contexto = {
            'tarefa': tarefa,
            'status_anterior': instance.status_anterior,
            'novo_status': instance.novo_status,  
            'alterado_por': instance.alterado_por,
        }

        # Chama nossa função centralizada de envio de e-mail
        enviar_email_tarefa(
            assunto=f"Status da tarefa '{tarefa.titulo}' foi alterado",
            template_texto='tarefas/emails/email_notificacao_status.txt',
            template_html='tarefas/emails/email_notificacao_status.html', # Lembre-se de criar este arquivo
            contexto=contexto,
            destinatarios=list(destinatarios)
        )