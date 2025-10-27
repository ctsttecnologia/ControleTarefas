
# seu_projeto/celery.py
import os
from celery import Celery

# Corrija para apontar para o módulo de configurações REAL: gerenciandoTarefas
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gerenciandoTarefas.settings')

# Corrija para usar o nome do projeto (ou o nome do módulo onde este arquivo está)
app = Celery('gerenciandoTarefas')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
