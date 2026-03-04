
# notifications/views.py

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Notificacao


@login_required
@require_POST
def marcar_como_lida(request, pk):
    """Marca uma notificação como lida e redireciona para url_destino."""
    notificacao = get_object_or_404(
        Notificacao, pk=pk, usuario=request.user
    )
    notificacao.marcar_como_lida()

    # Se veio via HTMX ou AJAX, retorna JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'id': pk})

    # Senão, redireciona para o destino da notificação
    if notificacao.url_destino:
        return redirect(notificacao.url_destino)

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
def marcar_todas_como_lidas(request):
    """Marca TODAS as notificações do usuário como lidas."""
    from django.utils import timezone

    atualizadas = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    ).update(lida=True, data_leitura=timezone.now())

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'count': atualizadas})

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def api_contagem(request):
    """Endpoint leve para polling do contador (usado por JS)."""
    count = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    ).count()

    return JsonResponse({'count': count})

