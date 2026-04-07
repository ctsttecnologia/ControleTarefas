
# usuario/context_processors.py

from notifications.context_processors import MAX_DROPDOWN
from notifications.models import Notificacao


def usuario_filial_context(request):
    """
    Injeta informações da filial ativa e das filiais permitidas em todos os templates.
    """
    if request.user.is_authenticated:
        filial_ativa = getattr(request.user, 'filial_ativa', None)
        filiais_permitidas = request.user.filiais_permitidas.all()
        
        return {
            'filial_ativa_global': filial_ativa,
            'filiais_permitidas_global': filiais_permitidas,
        }
    return {}

