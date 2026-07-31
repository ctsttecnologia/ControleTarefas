
# signals.py
import cloudinary.uploader
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import FotoRelatorio


@receiver(post_delete, sender=FotoRelatorio)
def deletar_imagem_cloudinary(sender, instance, **kwargs):
    if instance.imagem:
        try:
            cloudinary.uploader.destroy(instance.imagem.public_id)
        except Exception:
            # Evita quebrar a exclusão do registro se a chamada à API falhar
            pass
