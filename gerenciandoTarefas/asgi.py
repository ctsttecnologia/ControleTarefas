# gerenciandoTarefas/asgi.py
import os
from django.core.asgi import get_asgi_application

# 1. DEFINA A VARIÁVEL DE AMBIENTE PRIMEIRO!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gerenciandoTarefas.settings')

# 2. CHAME get_asgi_application() AQUI.
django_asgi_app = get_asgi_application()

# 3. AGORA que o Django carregou, importe o Channels e suas rotas de chat
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack 
import chat.routing

# 4. Configure a aplicação
application = ProtocolTypeRouter({
    # Use a variável que criamos para o HTTP
    "http": django_asgi_app, # <-- Esta linha é a correta
    
    # Conexões WebSocket (Channels)
    "websocket": AuthMiddlewareStack( 
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})



