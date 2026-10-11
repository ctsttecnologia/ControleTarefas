from django.apps import AppConfig

class PgrGestaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pgr_gestao'
    verbose_name = 'PGR - Programa de Gerenciamento de Riscos'

    def ready(self):
        from . import signals  # noqa: F401
