from django.apps import AppConfig
import os
import sys


class PgrGestaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pgr_gestao'
    verbose_name = 'PGR - Programa de Gerenciamento de Riscos'

    def ready(self):
        """
        Importa signals quando o app estiver pronto
        """
        try:
            # Ensure the app directory is in the Python path
            app_path = os.path.dirname(os.path.abspath(__file__))
            if app_path not in sys.path:
                sys.path.append(app_path)

            import pgr_gestao.signals
        except ImportError:
            pass


