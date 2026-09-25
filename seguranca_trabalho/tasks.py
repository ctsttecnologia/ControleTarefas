
# seguranca_trabalho/tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def anonimizar_dados_sensiveis_task():
    call_command('anonimizar_dados_sensiveis_sst')

