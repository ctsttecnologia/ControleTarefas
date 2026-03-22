# tributacao/apps.py

from django.apps import AppConfig


class TributacaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tributacao'
    verbose_name = 'Tributação'
