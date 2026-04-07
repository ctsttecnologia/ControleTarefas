
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    """Storage que resolve o path em runtime, sem hardcodar na migration."""

    def __init__(self, **kwargs):
        location = getattr(
            settings, 'PRIVATE_MEDIA_ROOT',
            os.path.join(settings.BASE_DIR, 'private_media')
        )
        kwargs.setdefault('location', location)
        kwargs.setdefault('base_url', '/private/')
        super().__init__(**kwargs)

    def deconstruct(self):
        """
        Retorna sem argumentos fixos — assim o Django NÃO serializa
        o path absoluto na migration.
        """
        return (
            'documentos.storage.PrivateMediaStorage',
            [],
            {},
        )

