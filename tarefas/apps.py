# tarefas/apps.py
from django.apps import AppConfig


class TarefasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tarefas'
    verbose_name = 'Tarefas'

    def ready(self):
        """Registra os signals quando o app é carregado."""
        from . import signals  # noqa: F401
