import os
from django.core.asgi import get_asgi_application


# 1. Configura o settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gerenciandoTarefas.settings')

# 2. Carrega o Django HTTP (Crucial fazer isso ANTES de importar o channels)
django_asgi_app = get_asgi_application()

# 3. Importações do Channels (Só agora!)
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# 4. Importa routing de forma segura
try:
    import chat.routing
    websocket_urlpatterns = chat.routing.websocket_urlpatterns
except ImportError:
    websocket_urlpatterns = []

# 5. Define o Roteador
application = ProtocolTypeRouter({
    # HTTP -> Django nativo
    "http": django_asgi_app,

    # WebSocket -> Django Channels
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})

