
# chat/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # WebSocket de notificações globais
    re_path(r'^ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    
    # WebSocket do chat por sala
    re_path(r'^ws/chat/(?P<room_id>[0-9a-f-]{36})/$', consumers.ChatConsumer.as_asgi()),
    
    # Suporte para WSS (HTTPS)
    re_path(r'^wss/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'^wss/chat/(?P<room_id>[0-9a-f-]{36})/$', consumers.ChatConsumer.as_asgi()),
]

print(f"🔧 WebSocket URLs configuradas: {len(websocket_urlpatterns)} rotas")



