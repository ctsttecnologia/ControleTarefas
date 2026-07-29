
# signals.py
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import FotoRelatorio


@receiver(post_delete, sender=FotoRelatorio)
def deletar_imagem_cloudinary(sender, instance, **kwargs):
    if instance.imagem:
        instance.imagem.delete(save=False)

