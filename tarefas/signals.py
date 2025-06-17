from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import Tarefas, HistoricoStatus

User = get_user_model()

@receiver(post_save, sender=HistoricoStatus)
def enviar_notificacao_status(sender, instance, created, **kwargs):
    if created:
        tarefa = instance.tarefa
        assunto = f"Status da tarefa '{tarefa.titulo}' foi alterado"
        mensagem = render_to_string('tarefas/email_notificacao_status.txt', {
            'tarefa': tarefa,
            'status_anterior': instance.status_anterior,
            'novo_status': instance.novo_status,
            'alterado_por': instance.alterado_por,
        })
        
        send_mail(
            assunto,
            mensagem,
            settings.DEFAULT_FROM_EMAIL,
            [tarefa.usuario.email],
            fail_silently=True,
        )