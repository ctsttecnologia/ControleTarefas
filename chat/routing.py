
# chat/routing.py
from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    # Aceita tanto 'ws/chat/...' quanto 'wss/chat/...' para garantir
    re_path(r'ws/chat/(?P<room_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'wss/chat/(?P<room_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),
    
    # Rota de notificações
    re_path(r'wss/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),

    # Rota para o socket de Notificações GERAIS
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
]