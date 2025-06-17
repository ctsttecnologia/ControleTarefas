from django.apps import AppConfig

class UsuarioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuario'
    
    def ready(self):
        # Importe signals aqui se necessário
        try:
            import usuario.signals
        except ImportError:
            pass