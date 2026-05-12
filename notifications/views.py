
# notifications/views.py

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.utils.dateparse import parse_datetime

from .models import Notificacao


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


def api_contagem(request):
    """
    Endpoint leve para polling do contador (usado por JS).
    
    🎯 NÃO usa @login_required: retorna 401 JSON em vez de redirect 302
    para evitar carregar a página de login em chamadas AJAX.
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'status': 'error', 'error': 'Autenticação necessária', 'count': 0},
            status=401,
        )

    count = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    ).count()

    return JsonResponse({'status': 'ok', 'count': count})

@login_required
def dropdown_html(request):
    """
    Retorna o HTML parcial do dropdown do sino (apenas a lista de notificações).
    Usado pelo JS para re-renderizar o dropdown quando chega notificação via WebSocket.
    """
    qs = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    )[:8]  # MAX_DROPDOWN
    
    return render(request, 'notifications/_dropdown_items.html', {
        'notification_list': qs,
        'notification_count': qs.count(),
    })

@login_required
def api_notificacoes_novas(request):
    """
    Retorna notificações criadas após o timestamp fornecido.
    
    GET /notificacoes/api/novas/?desde=2026-05-11T17:00:00Z
    """
    desde = request.GET.get('desde')
    
    qs = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    )
    
    if desde:
        timestamp = parse_datetime(desde)
        if timestamp:
            qs = qs.filter(criada_em__gt=timestamp)
    
    # Limita a 10 mais recentes pra não sobrecarregar
    notificacoes = qs.order_by('-criada_em')[:10]
    
    data = {
        'server_time': timezone.now().isoformat(),
        'total_nao_lidas': Notificacao.objects.filter(
            usuario=request.user, 
            lida=False
        ).count(),
        'novas': [
            {
                'id': n.id,
                'titulo': n.titulo,
                'mensagem': n.mensagem,
                'url': n.url or '',
                'tipo': getattr(n, 'tipo', 'info'),  # info|sucesso|aviso|erro
                'criada_em': n.criada_em.isoformat(),
                'icone': getattr(n, 'icone', '🔔'),
            }
            for n in notificacoes
        ],
    }
    
    return JsonResponse(data)