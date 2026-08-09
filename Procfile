
web: /home/application/app/venv/bin/daphne gerenciandoTarefas.asgi:application --port 8000 --bind 0.0.0.0 -v 2
worker: /home/application/app/venv/bin/celery -A gerenciandoTarefas worker -l info --concurrency=2 --max-tasks-per-child=1000
beat: /home/application/app/venv/bin/celery -A gerenciandoTarefas beat -l info --schedule=/home/application/tmp/celerybeat-schedule
