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
import chat.routing

# 4. Define o Roteador
application = ProtocolTypeRouter({
    # http -> Django nativo
    "http": django_asgi_app,

    # websocket -> Django Channels
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns
            )
        )
    ),
})


