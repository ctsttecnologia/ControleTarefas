
# ferramentas/tasks.py 
import logging
from celery import shared_task
from .models import Ferramenta, MalaFerramentas

logger = logging.getLogger(__name__)


@shared_task(name="ferramentas.gerar_qrcodes")
def gerar_qrcodes_task(forcar=False):
    """
    Gera QR Codes de ferramentas e malas.
    forcar=False: só os registros sem QR.
    forcar=True : recria todos (use após perder arquivos de mídia).
    """
    total = 0
    for Model in (Ferramenta, MalaFerramentas):
        for obj in Model._base_manager.all().iterator():
            if not forcar and obj.qr_code:
                continue
            try:
                obj.qr_code = ""      # o save() só gera se o campo estiver vazio
                obj.save()
                total += 1
            except Exception:
                logger.exception("Falha ao gerar QR %s pk=%s", Model.__name__, obj.pk)
    logger.info("QR Codes gerados: %s (forcar=%s)", total, forcar)
    return total


