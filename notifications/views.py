
# notifications/views.py

from venv import logger
import logging
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_datetime
from .models import Notificacao

MAX_DROPDOWN = 8

logger = logging.getLogger(__name__)

@login_required
def notificacao_list(request):
    """Página completa com todas as notificações do usuário."""
    qs = Notificacao.objects.filter(usuario=request.user).order_by('-data_criacao')

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


def _is_ajax(request):
    """Detecta requisições AJAX/HTMX/Fetch."""
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.headers.get('HX-Request') == 'true'
        or 'application/json' in request.headers.get('Accept', '')
    )


@login_required
def marcar_como_lida(request, pk):
    """Marca uma notificação como lida e redireciona para url_destino."""
    notificacao = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
    notificacao.marcar_como_lida()

    if _is_ajax(request):
        return JsonResponse({'status': 'ok', 'id': pk})

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

    if _is_ajax(request):
        return JsonResponse({'status': 'ok', 'count': atualizadas})
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def api_contagem(request):
    """Retorna apenas a contagem de notificações não lidas (leve e rápido)."""
    try:
        total = Notificacao.objects.filter(
            usuario=request.user,
            lida=False
        ).count()

        return JsonResponse({
            'total_nao_lidas': total,
            'server_time': timezone.now().isoformat(),
        })
    except Exception:
        logger.exception("Erro em api_contagem")
        return JsonResponse({
            'total_nao_lidas': 0,
            'server_time': timezone.now().isoformat(),
        }, status=200)

@login_required
def dropdown_html(request):
    """
    Retorna o HTML parcial do dropdown do sino (apenas a lista de notificações).
    Usado pelo JS para re-renderizar o dropdown quando chega notificação
    via WebSocket ou ao voltar para a aba.
    """
    # Conta o total de não lidas ANTES de aplicar slice
    total_nao_lidas = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    ).count()

    # Busca apenas as N mais recentes para exibir no dropdown
    notificacoes = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    ).order_by('-data_criacao')[:MAX_DROPDOWN]

    return render(request, 'notifications/_dropdown_items.html', {
        'notification_list': notificacoes,
        'notification_count': total_nao_lidas,   # total real, não limitado a 8
        'tem_mais': total_nao_lidas > MAX_DROPDOWN,
    })

@login_required
def api_notificacoes_novas(request):
    """Retorna as notificações novas desde o último polling."""
    try:
        desde = request.GET.get('desde')
        agora = timezone.now()

        qs = Notificacao.objects.filter(usuario=request.user)

        if desde:
            timestamp = parse_datetime(desde)
            if timestamp:
                qs = qs.filter(data_criacao__gt=timestamp)

        notificacoes_qs = qs.order_by('-data_criacao')[:20]

        novas = [{
            'id': n.id,
            'titulo': n.titulo,
            'mensagem': n.mensagem,
            'tipo': getattr(n, 'tipo', 'info'),
            'url': n.url_destino or '',
            'icone': getattr(n, 'icone', '') or '',
            'data_criacao': n.data_criacao.isoformat(),
        } for n in notificacoes_qs]

        total_nao_lidas = Notificacao.objects.filter(
            usuario=request.user,
            lida=False
        ).count()

        return JsonResponse({
            'novas': novas,
            'total_nao_lidas': total_nao_lidas,
            'server_time': agora.isoformat(),
        })

    except Exception:
        logger.exception("Erro em api_notificacoes_novas")
        return JsonResponse({
            'novas': [],
            'total_nao_lidas': 0,
            'server_time': timezone.now().isoformat(),
        }, status=200)