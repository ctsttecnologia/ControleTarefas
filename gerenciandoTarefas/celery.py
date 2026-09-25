
# gerenciandoTarefas/celery.py
from __future__ import absolute_import, unicode_literals
import os
import sys
from celery.schedules import crontab


CELERY_BEAT_SCHEDULE = {
    'anonimizar-dados-sensiveis-sst-mensal': {
        'task': 'seguranca_trabalho.tasks.anonimizar_dados_sensiveis_task',
        'schedule': crontab(day_of_month=1, hour=3, minute=0),  # 1x/mês
    },
}

# Monkey patch do eventlet APENAS se estiver rodando um worker com eventlet.
# Isso evita o conflito com o `runserver` do Django.
if 'celery' in sys.argv[0] and 'eventlet' in ''.join(sys.argv):
    import eventlet
    eventlet.monkey_patch()

from celery import Celery

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gerenciandoTarefas.settings')

app = Celery('gerenciandoTarefas')

# Usando uma string aqui significa que o worker não precisa serializar
# o objeto de configuração para processos filhos.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carregar módulos de task de todas as aplicações Django registradas.
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


