
# notifications/views.py
import logging

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from .realtime import push_notification_count, push_notification_read

from .models import Notificacao

MAX_DROPDOWN = 8
MAX_NOVAS = 20
PAGE_SIZE = 30
logger = logging.getLogger(__name__)


# ───────── helpers ─────────
def _is_ajax(request):
    h = request.headers
    return (
        h.get('X-Requested-With') == 'XMLHttpRequest'
        or h.get('HX-Request') == 'true'
        or 'application/json' in h.get('Accept', '')
    )


def _safe_redirect(request, url, fallback='/'):
    """Redireciona apenas para URLs do próprio host."""
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(url)
    return redirect(fallback)


def _parse_desde(valor):
    """ISO 8601 -> datetime aware, ou None se inválido."""
    if not valor:
        return None
    # '+' na querystring vira espaço: '...00:00:00 00:00'
    valor = str(valor).strip().replace(' ', '+')
    try:
        dt = parse_datetime(valor)
    except ValueError:
        return None
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _nao_lidas(user):
    return Notificacao.objects.filter(usuario=user, lida=False)


# ───────── páginas ─────────
@login_required
def notificacao_list(request):
    user = request.user
    qs = Notificacao.objects.filter(usuario=user).order_by('-data_criacao')

    filtro = request.GET.get('filtro', 'todas')
    if filtro == 'nao_lidas':
        qs = qs.filter(lida=False)
    elif filtro == 'lidas':
        qs = qs.filter(lida=True)

    categoria = request.GET.get('categoria', '')
    if categoria:
        qs = qs.filter(categoria=categoria)

    notificacoes = Paginator(qs, PAGE_SIZE).get_page(request.GET.get('page'))

    return render(request, 'notifications/notificacao_list.html', {
        'notificacoes': notificacoes,
        'filtro': filtro,
        'categoria': categoria,
        'nao_lidas_count': _nao_lidas(user).count(),
        'titulo_pagina': 'Notificações',
    })


# ───────── ações ─────────
@login_required
def marcar_como_lida(request, pk):
    notificacao = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
    if not notificacao.lida:
        notificacao.marcar_como_lida()
        transaction.on_commit(lambda: push_notification_read(request.user, pk))

    if _is_ajax(request):
        return JsonResponse({'status': 'ok', 'id': pk})

    fallback = request.META.get('HTTP_REFERER') or '/'
    return _safe_redirect(request, notificacao.url_destino or fallback, '/')




@login_required
@require_POST
def marcar_todas_como_lidas(request):
    atualizadas = _nao_lidas(request.user).update(
        lida=True, data_leitura=timezone.now(),
    )
    transaction.on_commit(lambda: push_notification_count(request.user, 0))

    if _is_ajax(request):
        return JsonResponse({'status': 'ok', 'count': atualizadas})
    return _safe_redirect(request, request.META.get('HTTP_REFERER'), '/')


# ───────── APIs (polling / fallback) ─────────
@never_cache
@login_required
@require_GET
def api_contagem(request):
    try:
        total = _nao_lidas(request.user).count()
    except Exception:
        logger.exception("Erro em api_contagem")
        return JsonResponse({'error': 'internal'}, status=500)

    return JsonResponse({
        'count': total,
        'total_nao_lidas': total,
        'server_time': timezone.now().isoformat(),
    })


@never_cache
@login_required
@require_GET
def dropdown_html(request):
    itens = list(_nao_lidas(request.user).order_by('-data_criacao')[:MAX_DROPDOWN])
    cheio = len(itens) == MAX_DROPDOWN
    total = _nao_lidas(request.user).count() if cheio else len(itens)

    return render(request, 'notifications/_dropdown_items.html', {
        'notification_list': itens,
        'notification_count': total,
        'tem_mais': total > MAX_DROPDOWN,
    })


@never_cache
@login_required
@require_GET
def api_notificacoes_novas(request):
    try:
        agora = timezone.now()
        desde = _parse_desde(request.GET.get('desde'))

        qs = _nao_lidas(request.user)
        if desde:
            qs = qs.filter(data_criacao__gt=desde)

        rows = list(qs.order_by('-data_criacao')[:MAX_NOVAS])
        rows.reverse()  # cronológico (mais antiga primeiro)

        novas = [{
            'id': n.id,
            'titulo': n.titulo,
            'mensagem': n.mensagem,
            'tipo': getattr(n, 'tipo', 'info'),
            'url': n.url_destino or '',
            'icone': getattr(n, 'icone', '') or '',
            'data_criacao': n.data_criacao.isoformat(),
        } for n in rows]

        return JsonResponse({
            'novas': novas,
            'total_nao_lidas': _nao_lidas(request.user).count(),
            'server_time': agora.isoformat(),
        })
    except Exception:
        logger.exception("Erro em api_notificacoes_novas")
        return JsonResponse({'error': 'internal'}, status=500)

