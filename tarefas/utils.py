
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

# Configura um logger para capturar erros de e-mail
logger = logging.getLogger(__name__)

def enviar_email_notificacao_status(tarefa, usuario_notificado, status_anterior, novo_status, request):
    """
    Renderiza e envia um e-mail de notificação (texto e HTML) 
    sobre a mudança de status de uma tarefa.
    """
    # Garante que não tentaremos enviar e-mail para um usuário sem e-mail ou não definido
    if not usuario_notificado or not usuario_notificado.email:
        logger.warning(f"Tentativa de notificar usuário sem e-mail para a tarefa {tarefa.pk}.")
        return

    assunto = f"Atualização na Tarefa: {tarefa.titulo}"
    contexto = {
        'tarefa': tarefa,
        'usuario': usuario_notificado,
        'status_anterior': status_anterior,
        'novo_status': novo_status,
        'request': request,
    }

    try:
        # Renderiza as duas versões do e-mail
        corpo_texto = render_to_string('tarefas/email_notificacao_status.txt', contexto)
        corpo_html = render_to_string('tarefas/email_notificacao_status.html', contexto)

        # Cria o e-mail e anexa a versão HTML
        email = EmailMultiAlternatives(
            subject=assunto,
            body=corpo_texto,
            from_email=settings.DEFAULT_FROM_EMAIL, # Boa prática: usar o e-mail das configurações
            to=[usuario_notificado.email]
        )
        email.attach_alternative(corpo_html, "text/html")
        email.send()
        logger.info(f"E-mail de notificação enviado para {usuario_notificado.email} sobre a tarefa {tarefa.pk}.")

    except Exception as e:
        # Captura qualquer erro durante o envio (ex: falha no servidor SMTP)
        # e o registra, para não quebrar a aplicação inteira.
        logger.error(f"Falha ao enviar e-mail de notificação para a tarefa {tarefa.pk}: {e}")
