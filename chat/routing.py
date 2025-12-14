
# chat/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # WebSocket de notificações globais (resolve o erro do seu terminal)
    re_path(r'^ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    
    # WebSocket do chat por sala
    re_path(r'^ws/chat/(?P<room_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),
]


