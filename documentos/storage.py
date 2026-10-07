
# documentos/storage.py
import requests
import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils
from cloudinary.exceptions import NotFound
from django.core.files.base import ContentFile
from cloudinary_storage.storage import RawMediaCloudinaryStorage
import uuid
import logging

logger = logging.getLogger(__name__)

class PrivateMediaStorage(RawMediaCloudinaryStorage):
    """
    Documentos sensíveis no Cloudinary: resource_type='raw', type='authenticated'
    (acesso só por URL assinada). public_id = name, sem prefixo nem sufixo aleatório.
    """
    RT = 'raw'
    DT = 'authenticated'

    def private_document_path(instance, filename):
        if instance.content_type_id:
            app_label = instance.content_type.app_label
            obj_id = instance.object_id or 0
        else:
            app_label = 'empresa'
            obj_id = instance.cliente_id or instance.filial_id or 0
        return f'documentos/{app_label}/{obj_id}/{uuid.uuid4().hex[:8]}_{filename}'

    def _pid(self, name):
        return name.replace('\\', '/')

    def get_available_name(self, name, max_length=None):
        return self._pid(name)

    def _save(self, name, content):
        pid = self._pid(name)
        if hasattr(content, 'seek'):
            content.seek(0)
        cloudinary.uploader.upload(
            content,
            public_id=pid,
            resource_type=self.RT,
            type=self.DT,
            overwrite=True,
            invalidate=True,
            unique_filename=False,
            use_filename=False,
        )
        return pid

    def _resource(self, name):
        return cloudinary.api.resource(self._pid(name), resource_type=self.RT, type=self.DT)

    def exists(self, name):
        try:
            self._resource(name)
            return True
        except NotFound:
            return False

    def size(self, name):
        try:
            return self._resource(name)['bytes']
        except NotFound:
            return 0

    def url(self, name):
        return cloudinary.utils.cloudinary_url(
            self._pid(name),
            resource_type=self.RT,
            type=self.DT,
            sign_url=True,
            secure=True,
        )[0]

    def _open(self, name, mode='rb'):
        url = cloudinary.utils.private_download_url(
            self._pid(name), '',
            resource_type=self.RT, type=self.DT,
        )
        resp = requests.get(url, timeout=30)
        if resp.status_code == 404:
            raise FileNotFoundError(name)
        if resp.status_code != 200:
            logger.error("Cloudinary %s em %s: %s",
                         resp.status_code, name, resp.headers.get('x-cld-error'))
            resp.raise_for_status()
        return ContentFile(resp.content, name=name)

    def delete(self, name):
        cloudinary.uploader.destroy(
            self._pid(name), resource_type=self.RT, type=self.DT, invalidate=True
        )

    def deconstruct(self):
        return ('documentos.storage.PrivateMediaStorage', [], {})
