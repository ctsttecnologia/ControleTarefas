
# diagnostico/middleware.py
import time
import logging
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)

class DetectarErro502Middleware:
    """Middleware simplificado para detectar possíveis causas de 502"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_response_time = 25  # Hospedagem elástica geralmente tem timeout de 30s
    
    def __call__(self, request):
        start_time = time.time()
        
        try:
            response = self.get_response(request)
            duration = time.time() - start_time
            
            # Log requisições que podem causar 502
            if duration > self.max_response_time:
                logger.error(
                    f"POSSÍVEL CAUSA 502 - Requisição muito lenta: "
                    f"Path: {request.path} | "
                    f"Method: {request.method} | "
                    f"Duration: {duration:.2f}s | "
                    f"User: {getattr(request.user, 'username', 'Anonymous')}"
                )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log detalhado para debug
            logger.error(
                f"ERRO INTERNO - Possível 502: "
                f"Path: {request.path} | "
                f"Error: {str(e)} | "
                f"Duration: {duration:.2f}s"
            )
            
            # Em produção, retorna erro genérico
            if not settings.DEBUG:
                return JsonResponse({
                    'error': 'Internal Server Error',
                    'status': 500
                }, status=500)
            
            raise  # Em desenvolvimento, deixa o Django mostrar o erro
