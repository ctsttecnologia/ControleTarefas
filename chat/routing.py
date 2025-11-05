
# chat/routing.py
from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    # Rota para o chat DENTRO de uma sala
    re_path(r'ws/chat/(?P<room_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),
    
    # ✅ NOVO: Rota para o socket de Notificações GERAIS
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
]