
# notifications/tasks.py

"""
Tasks Celery para notificações periódicas.
"""

from celery import shared_task
from django.core.management import call_command


@shared_task(name='notifications.gerar_notificacoes')
def gerar_notificacoes_task():
    """
    Executa o management command gerar_notificacoes via Celery.
    Agendado diariamente pelo CELERY_BEAT_SCHEDULE.
    """
    call_command('gerar_notificacoes')
    return 'Notificações geradas com sucesso!'



