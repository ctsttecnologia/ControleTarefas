
# notifications/context_processors.py

"""
Context processor unificado de notificações.
Substitui o notification_processor do app tarefas.
"""

from .models import Notificacao

# Máximo de notificações exibidas no dropdown
MAX_DROPDOWN = 8


def notification_processor(request):
    """Injeta notificações não lidas no contexto global."""
    if not request.user.is_authenticated:
        return {}

    notificacoes_nao_lidas = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    )

    return {
        'notification_count': notificacoes_nao_lidas.count(),
        'notification_list': notificacoes_nao_lidas[:MAX_DROPDOWN],
        'notificacao_list': list(notificacoes_nao_lidas[:MAX_DROPDOWN]),
    }

