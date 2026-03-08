
# notifications/views.py

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Notificacao



@login_required
def notificacao_list(request):
    """Página completa com todas as notificações do usuário."""
    qs = Notificacao.objects.filter(
        usuario=request.user,
    ).order_by('-data_criacao')
    # Filtro por status
    filtro = request.GET.get('filtro', 'todas')
    if filtro == 'nao_lidas':
        qs = qs.filter(lida=False)
    elif filtro == 'lidas':
        qs = qs.filter(lida=True)
    # Filtro por categoria
    categoria = request.GET.get('categoria', '')
    if categoria:
        qs = qs.filter(categoria=categoria)
    paginator = Paginator(qs, 30)
    page = request.GET.get('page')
    notificacoes = paginator.get_page(page)
    nao_lidas_count = Notificacao.objects.filter(
        usuario=request.user, lida=False,
    ).count()
    context = {
        'notificacoes': notificacoes,
        'filtro': filtro,
        'categoria': categoria,
        'nao_lidas_count': nao_lidas_count,
        'titulo_pagina': 'Notificações',
    }
    return render(request, 'notifications/notificacao_list.html', context)
@login_required
def marcar_como_lida(request, pk):
    """
    Marca uma notificação como lida e redireciona para url_destino.
    Aceita GET (clique no dropdown) e POST (AJAX/HTMX).
    """
    notificacao = get_object_or_404(
        Notificacao, pk=pk, usuario=request.user,
    )
    notificacao.marcar_como_lida()
    # Se veio via AJAX, retorna JSON
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

@login_required
def api_contagem(request):
    """Endpoint leve para polling do contador (usado por JS)."""
    count = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    ).count()

    return JsonResponse({'count': count})

