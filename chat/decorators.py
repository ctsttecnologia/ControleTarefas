
# chat/decorators.py
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
import time

def rate_limit_messages(max_messages=30, period=60):
    """Limita quantidade de mensagens por período"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Não autenticado'}, status=401)
            
            cache_key = f"chat_rate_{request.user.id}"
            
            # Obtém contagem atual
            data = cache.get(cache_key, {'count': 0, 'reset': time.time() + period})
            
            # Verifica se período expirou
            if time.time() > data['reset']:
                data = {'count': 0, 'reset': time.time() + period}
            
            # Verifica limite
            if data['count'] >= max_messages:
                wait_time = int(data['reset'] - time.time())
                return JsonResponse({
                    'error': f'Muitas mensagens. Aguarde {wait_time}s',
                    'retry_after': wait_time
                }, status=429)
            
            # Incrementa contador
            data['count'] += 1
            cache.set(cache_key, data, timeout=period + 10)
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

