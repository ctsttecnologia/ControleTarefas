from storages.backends.gcloud import GoogleCloudStorage


class StaticStorage(GoogleCloudStorage):
    location = 'static'
    default_acl = None


class MediaStorage(GoogleCloudStorage):
    location = 'media'
    default_acl = None
    file_overwrite = False


