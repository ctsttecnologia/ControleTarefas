
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)

def enviar_email_tarefa(assunto, template_texto, template_html, contexto, destinatarios):
    """
    Função genérica e centralizada para enviar e-mails de tarefas (texto e HTML).

    Args:
        assunto (str): O assunto do e-mail.
        template_texto (str): Caminho para o template de texto plano.
        template_html (str): Caminho para o template HTML.
        contexto (dict): Dicionário com dados para o template.
        destinatarios (list): Lista de strings de e-mails dos destinatários.
    """
    # Filtra e-mails vazios ou nulos da lista de destinatários para evitar erros.
    destinatarios_validos = [email for email in destinatarios if email]
    if not destinatarios_validos:
        logger.warning(f"Nenhum destinatário válido fornecido para o e-mail: '{assunto}'.")
        return

    try:
        corpo_texto = render_to_string(template_texto, contexto)
        corpo_html = render_to_string(template_html, contexto)

        email = EmailMultiAlternatives(
            subject=assunto,
            body=corpo_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios_validos,
        )
        email.attach_alternative(corpo_html, "text/html")
        email.send()
        logger.info(f"E-mail '{assunto}' enviado com sucesso para {destinatarios_validos}.")

    except Exception as e:
        # Captura qualquer erro (template não encontrado, falha no servidor SMTP) e registra.
        logger.error(f"Falha ao enviar e-mail '{assunto}': {e}", exc_info=True)
