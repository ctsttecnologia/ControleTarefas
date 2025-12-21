
<!--echo web: gunicorn gerenciandoTarefas.asgi:application --bind 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker --workers 2 --timeout 120 --max-requests 1000 > Procfile-->

<!--web: gunicorn gerenciandoTarefas.wsgi:application --bind 0.0.0.0:8000-->

<!--echo web: waitress-serve --host=0.0.0.0 --port=$PORT gerenciandoTarefas.wsgi:application > Procfile-->

<!--echo web: daphne gerenciandoTarefas.asgi:application --port $PORT --bind 0.0.0.0 > Procfile-->

echo web: daphne gerenciandoTarefas.asgi:application --port $PORT --bind 0.0.0.0 > Procfile






