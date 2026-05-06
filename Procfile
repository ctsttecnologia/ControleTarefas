web: daphne gerenciandoTarefas.asgi:application --port 8000 --bind 0.0.0.0 -v 2
worker: celery -A gerenciandoTarefas worker -l info --concurrency=2 --max-tasks-per-child=1000
beat: celery -A gerenciandoTarefas beat -l info --schedule=/home/application/tmp/celerybeat-schedule
