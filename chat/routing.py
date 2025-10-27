
# chat/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Este regex aceita um UUID (o ID da sala)
    re_path(r'ws/chat/(?P<room_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),
]
