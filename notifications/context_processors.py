from .models import Notificacao

MAX_DROPDOWN = 8


def notification_processor(request):
    """Injeta notificações não lidas no contexto global."""
    if not request.user.is_authenticated:
        return {}

    try:
        qs = Notificacao.objects.filter(
            usuario=request.user,
            lida=False,
        )
        return {
            'notification_count': qs.count(),          
            'notification_list': qs[:MAX_DROPDOWN],   
        }
    except Exception as e:
        print(f"[ERROR] notification_processor: {e}")
        return {'notification_count': 0, 'notification_list': []}


