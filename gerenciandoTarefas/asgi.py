# ASGI config for gerenciandoTarefas

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
    # Adicione este print para confirmar que deu certo
    print(f"✅ Rotas de WebSocket importadas com sucesso: {len(websocket_urlpatterns)} rotas encontradas.")
except Exception as e:
    # Captura QUALQUER erro e o imprime no console
    print(f"❌ ERRO CRÍTICO ao importar 'chat.routing': {e}")
    print("❌ O WebSocket NÃO irá funcionar até que este erro seja corrigido.")
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

