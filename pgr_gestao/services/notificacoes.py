
# pgr_gestao/services/notificacoes.py
import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def enviar(destino_setting, assunto, mensagem):
    destino = getattr(settings, destino_setting, None)
    if not destino:
        return
    try:
        send_mail(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [destino])
    except Exception:
        logger.exception("Falha ao enviar e-mail (%s)", destino_setting)

