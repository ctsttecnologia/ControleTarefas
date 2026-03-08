# suprimentos/apps.py

from django.apps import AppConfig


class SuprimentosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'suprimentos'

    def ready(self):
        import suprimentos.signals  # noqa: F401

