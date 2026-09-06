

# gerenciandoTarefas/__init__.py
from __future__ import absolute_import, unicode_literals

# Isso garante que o app seja sempre importado quando
# Django iniciar para que shared_task funcione
from .celery import app as celery_app

__all__ = ('celery_app',)

