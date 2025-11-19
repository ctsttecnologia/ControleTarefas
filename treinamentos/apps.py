# treinamentos/apps.py
from django.apps import AppConfig

class TreinamentosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'treinamentos'
    
    def ready(self):
            # Importa os signals quando o app estiver pronto
            import treinamentos.signals