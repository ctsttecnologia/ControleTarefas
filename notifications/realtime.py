
# notifications/realtime.py
"""
Helpers para enviar atualizações em tempo real via WebSocket
para o NotificationConsumer.

Uso típico:
    from notifications.realtime import push_notification_count, push_new_notification

    push_notification_count(user)              # atualiza apenas o badge
    push_new_notification(user, notificacao)   # envia toast + atualiza badge

Resiliência:
    Se o Redis estiver indisponível (channels_redis), as funções degradam
    silenciosamente — a notificação continua salva no banco, apenas o
    push em tempo real é pulado. Isso evita travar rotinas batch quando
    o Redis está offline em dev.
"""
import logging
from typing import Optional, Union

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

# ───────────────────────────────────────────────────────────────────────
# Detecção de erros de conexão (Redis / rede)
# ───────────────────────────────────────────────────────────────────────
# Importa de forma defensiva: se redis não estiver instalado, usa OSError
# como fallback (ConnectionRefusedError herda dele).
try:
    from redis.exceptions import (
        ConnectionError as RedisConnectionError,
        TimeoutError as RedisTimeoutError,
    )
    _CONNECTION_ERRORS: tuple = (
        RedisConnectionError, RedisTimeoutError, ConnectionRefusedError, OSError,
    )
except ImportError:  # pragma: no cover
    _CONNECTION_ERRORS = (ConnectionRefusedError, OSError)


# ───────────────────────────────────────────────────────────────────────
# Helpers internos
# ───────────────────────────────────────────────────────────────────────

def _group_name(user_id: int) -> str:
    """Nome do grupo Channels — DEVE bater com NotificationConsumer."""
    return f"notifications_{user_id}"


def _resolve_user_id(user) -> Optional[int]:
    """Aceita instância de User ou int e retorna user_id."""
    if user is None:
        return None
    if isinstance(user, int):
        return user
    if hasattr(user, 'pk') and user.pk:
        return user.pk
    return None


def _serialize_notificacao(notificacao) -> dict:
    """Converte uma Notificacao em dict serializável para envio via WS."""
    return {
        'id': notificacao.pk,
        'tipo': notificacao.tipo,
        'tipo_display': notificacao.get_tipo_display(),
        'categoria': notificacao.categoria,
        'categoria_display': notificacao.get_categoria_display(),
        'prioridade': notificacao.prioridade,
        'titulo': notificacao.titulo,
        'mensagem': notificacao.mensagem or '',
        'icone': notificacao.icone,
        'url_destino': notificacao.url_destino or '',
        'lida': notificacao.lida,
        'data_criacao': notificacao.data_criacao.isoformat(),
        'tempo_relativo': notificacao.tempo_relativo,
        'badge_class': notificacao.badge_class,
    }


def _safe_group_send(channel_layer, group: str, message: dict, *, ctx: str) -> bool:
    """
    Wrapper que executa group_send protegendo contra Redis offline.

    Args:
        channel_layer: instância do channel layer (já validada)
        group:   nome do grupo Channels
        message: payload do evento
        ctx:     descrição curta do contexto (para logs)

    Returns:
        True  -> push enviado
        False -> Redis offline OU outro erro (não-fatal)
    """
    try:
        async_to_sync(channel_layer.group_send)(group, message)
        return True

    except _CONNECTION_ERRORS as e:
        # Redis offline → degrada silenciosamente. Log curto, sem stack trace.
        # Usa nível WARNING (não ERROR) porque é uma condição esperada em dev.
        logger.warning(
            "⚠ Redis indisponível — push WS pulado [%s, group=%s]: %s",
            ctx, group, str(e).splitlines()[0][:120],
        )
        return False

    except Exception as e:
        # Erro inesperado (bug real) → loga com stack trace completo.
        logger.exception(
            "Erro inesperado no push WS [%s, group=%s]: %s",
            ctx, group, e,
        )
        return False


# ───────────────────────────────────────────────────────────────────────
# API pública
# ───────────────────────────────────────────────────────────────────────

def push_notification_count(
    user: Union['User', int, None],
    count: Optional[int] = None,
) -> bool:
    """
    Envia a contagem de notificações não lidas via WebSocket.
    Atualiza o badge do sino em tempo real.

    Args:
        user:  instância de User OU user_id (int)
        count: contagem opcional pré-calculada. Se None, calcula do banco.

    Returns:
        True se o evento foi enviado com sucesso, False caso contrário.
    """
    user_id = _resolve_user_id(user)
    if user_id is None:
        logger.debug("push_notification_count: user inválido (%r)", user)
        return False

    if count is None:
        try:
            from .models import Notificacao
            count = Notificacao.objects.filter(
                usuario_id=user_id, lida=False,
            ).count()
        except Exception as e:
            logger.exception(
                "Erro ao contar não lidas (user=%s): %s", user_id, e,
            )
            return False

    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.debug("Channel layer não configurado — push ignorado")
        return False

    ok = _safe_group_send(
        channel_layer,
        _group_name(user_id),
        {
            'type': 'notification_count_update',
            'count': int(count),
        },
        ctx=f"count user={user_id}",
    )
    if ok:
        logger.debug("📡 Push contagem: user=%s count=%s", user_id, count)
    return ok


def push_new_notification(user, notificacao) -> bool:
    """
    Envia uma nova notificação completa (para toast/popup) +
    atualiza o badge.

    Args:
        user:        instância de User (ou user_id)
        notificacao: instância de Notificacao

    Returns:
        True se enviou com sucesso.
    """
    user_id = _resolve_user_id(user)
    if user_id is None:
        return False

    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.debug("Channel layer não configurado — push ignorado")
        return False

    # 1) Evento de "nova notificação" (toast/popup no front)
    payload = _serialize_notificacao(notificacao)
    ok_new = _safe_group_send(
        channel_layer,
        _group_name(user_id),
        {
            'type': 'new_notification',
            'notification': payload,
        },
        ctx=f"new user={user_id} notif={notificacao.pk}",
    )

    # 2) Atualiza badge (mesmo se o push acima falhar — tenta de novo)
    #    Se Redis estiver offline, ambos retornam False rapidamente.
    ok_count = push_notification_count(user_id)

    if ok_new:
        logger.debug(
            "📡 Push nova notificação: user=%s notif=%s tipo=%s",
            user_id, notificacao.pk, notificacao.tipo,
        )
    return ok_new and ok_count


def push_notification_read(user, notificacao_id: int) -> bool:
    """
    Notifica o cliente que uma notificação foi marcada como lida
    (útil para sincronizar múltiplas abas/dispositivos).
    """
    user_id = _resolve_user_id(user)
    if user_id is None:
        return False

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return False

    ok = _safe_group_send(
        channel_layer,
        _group_name(user_id),
        {
            'type': 'notification_read',
            'notification_id': notificacao_id,
        },
        ctx=f"read user={user_id} notif={notificacao_id}",
    )
    # Atualiza badge também
    push_notification_count(user_id)
    return ok
