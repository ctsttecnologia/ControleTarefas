
import os
from django.conf import settings
# documentos/storage.py
from cloudinary_storage.storage import RawMediaCloudinaryStorage


class PrivateMediaStorage(RawMediaCloudinaryStorage):
    """
    Storage privado para documentos sensíveis (PDFs, DOCX, etc).
    Usa RESOURCE_TYPE='raw' no Cloudinary (não é imagem).
    Delivery type deve ser 'authenticated' para exigir URL assinada.
    """

    def get_available_name(self, name, max_length=None):
        # mantém path previsível (sem sufixo aleatório), igual ao comportamento local
        return name

    def deconstruct(self):
        return ('documentos.storage.PrivateMediaStorage', [], {})