from django.apps import AppConfig


class SegurancaTrabalhoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'seguranca_trabalho'
    verbose_name = 'Segurança do Trabalho'

    def ready(self):
        from . import signals  # noqa: F401