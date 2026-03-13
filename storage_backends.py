"""
Backends de storage para Google Cloud Storage.
Só é importado em produção quando STORAGE_PROVIDER == 'GCS'.
"""

from django.conf import settings

try:
    from storages.backends.gcloud import GoogleCloudStorage

    class StaticStorage(GoogleCloudStorage):
        location = 'static'
        default_acl = None
        bucket_name = settings.GS_BUCKET_NAME
        project_id = settings.GS_PROJECT_ID
        credentials = settings.GS_CREDENTIALS

    class MediaStorage(GoogleCloudStorage):
        location = 'media'
        default_acl = None
        file_overwrite = False
        bucket_name = settings.GS_BUCKET_NAME
        project_id = settings.GS_PROJECT_ID
        credentials = settings.GS_CREDENTIALS

except ImportError:
    # Ambiente local sem django-storages instalado
    pass


