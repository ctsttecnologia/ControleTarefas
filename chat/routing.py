
# chat/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # WebSocket do chat
    re_path(r'wss/chat/(?P<room_id>[0-9a-f-]{36})/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<room_id>[0-9a-f-]{36})/$', consumers.ChatConsumer.as_asgi()),
    
    # WebSocket de notificações  
    re_path(r'wss/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]



