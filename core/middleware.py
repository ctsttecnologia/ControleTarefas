
# core/middleware.py

from django.shortcuts import render
from django.conf import settings


class MaintenanceModeMiddleware:
    """
    Middleware para ativar modo de manutenção.
    Configure MAINTENANCE_MODE = True no settings.py para ativar.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verifica se o modo de manutenção está ativo
        if getattr(settings, 'MAINTENANCE_MODE', False):
            # Permite que superusuários acessem mesmo em manutenção
            if not (request.user.is_authenticated and request.user.is_superuser):
                # Exclui URLs de admin e static
                if not request.path.startswith('/admin/') and not request.path.startswith('/static/'):
                    return render(request, 'errors/503.html', status=503)
        
        response = self.get_response(request)
        return response

