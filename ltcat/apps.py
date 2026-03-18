# ltcat/apps.py

from django.apps import AppConfig


class LtcatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ltcat"
    verbose_name = "LTCAT - Laudo Técnico das Condições Ambientais"

