
# chat/middleware.py
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        return User.objects.get(id=user_id)
    except (jwt.InvalidTokenError, User.DoesNotExist):
        return AnonymousUser()

class WebSocketAuthMiddleware(BaseMiddleware):
    """Middleware para autenticação WebSocket via token"""
    
    async def __call__(self, scope, receive, send):
        # Tenta obter token dos query params
        query_string = scope.get('query_string', b'').decode()
        token = None
        
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=')[1]
                break
        
        if token:
            scope['user'] = await get_user_from_token(token)
        
        return await super().__call__(scope, receive, send)

