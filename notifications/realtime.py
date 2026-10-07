# notifications/realtime.py
"""
Push em tempo real para o NotificationConsumer (grupo `notifications_<user_id>`).

Uso:
    push_notification_count(user)             # só o badge
    push_new_notification(user, notificacao)  # toast + badge
    push_notification_read(user, notif_id)    # sincroniza abas + badge

Todas retornam bool (True = enviado). Nunca levantam exceção: se o Redis
estiver offline ou NOTIFICATIONS_REALTIME_ENABLED=False, a notificação
continua salva no banco e apenas o push é ignorado.
"""
import logging
from typing import Any, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

logger = logging.getLogger(__name__)

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


# ─────────────────────────── helpers internos ───────────────────────────

def _enabled() -> bool:
    return bool(getattr(settings, "NOTIFICATIONS_REALTIME_ENABLED", True))


def _group_name(user_id: int) -> str:
    """Deve bater com NotificationConsumer.user_group_name."""
    return f"notifications_{user_id}"


def _resolve_user_id(user: Any) -> Optional[int]:
    """Aceita instância de User ou ID (int/str numérica)."""
    if user is None or isinstance(user, bool):
        return None
    if isinstance(user, int):
        return user
    if isinstance(user, str) and user.isdigit():
        return int(user)
    pk = getattr(user, "pk", None)
    return pk if pk else None


def _serialize_notificacao(n) -> dict:
    """Notificacao -> dict JSON-serializável."""
    return {
        "id": n.pk,
        "tipo": n.tipo,
        "tipo_display": n.get_tipo_display(),
        "categoria": n.categoria,
        "categoria_display": n.get_categoria_display(),
        "prioridade": n.prioridade,
        "titulo": n.titulo,
        "mensagem": n.mensagem or "",
        "icone": n.icone,
        "url_destino": n.url_destino or "",
        "lida": n.lida,
        "data_criacao": n.data_criacao.isoformat(),
        "tempo_relativo": n.tempo_relativo,
        "badge_class": n.badge_class,
    }


def _safe_group_send(group: str, message: dict, *, ctx: str) -> bool:
    """group_send tolerante a Redis offline. Nunca levanta exceção."""
    if not _enabled():
        return False

    layer = get_channel_layer()
    if layer is None:
        logger.debug("Channel layer não configurado [%s]", ctx)
        return False

    try:
        async_to_sync(layer.group_send)(group, message)
        return True
    except _CONNECTION_ERRORS as e:
        logger.warning("Redis indisponível no push WS [%s]: %s", ctx, e)
    except Exception:
        logger.exception("Erro inesperado no push WS [%s]", ctx)
    return False


# ───────────────────────────── API pública ──────────────────────────────

def push_notification_count(user, count: Optional[int] = None) -> bool:
    """Atualiza o badge do sino. Se `count` for None, consulta o banco."""
    if not _enabled():
        return False

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
        except Exception:
            logger.exception("Erro ao contar não lidas (user=%s)", user_id)
            return False

    return _safe_group_send(
        _group_name(user_id),
        {"type": "notification_count_update", "count": int(count)},
        ctx=f"count user={user_id}",
    )


def push_new_notification(user, notificacao) -> bool:
    """Envia toast com a notificação completa e atualiza o badge."""
    if not _enabled():
        return False

    user_id = _resolve_user_id(user)
    if user_id is None or notificacao is None:
        return False

    try:
        payload = _serialize_notificacao(notificacao)
    except Exception:
        logger.exception(
            "Erro ao serializar notificação (user=%s notif=%s)",
            user_id, getattr(notificacao, "pk", None),
        )
        return False

    ok_new = _safe_group_send(
        _group_name(user_id),
        {"type": "new_notification", "notification": payload},
        ctx=f"new user={user_id} notif={notificacao.pk}",
    )
    ok_count = push_notification_count(user_id)
    return ok_new and ok_count


def push_notification_read(user, notificacao_id: int) -> bool:
    """Sincroniza outras abas/dispositivos e atualiza o badge."""
    if not _enabled():
        return False

    user_id = _resolve_user_id(user)
    if user_id is None:
        return False

    ok_read = _safe_group_send(
        _group_name(user_id),
        {"type": "notification_read", "notification_id": notificacao_id},
        ctx=f"read user={user_id} notif={notificacao_id}",
    )
    ok_count = push_notification_count(user_id)
    return ok_read and ok_count


def push_unread_count(user_id, count: int, nova: Optional[dict] = None) -> bool:
    """[LEGADO] Compatibilidade. Se `nova` vier preenchida, envia o toast também."""
    ok = True
    if nova:
        ok = _safe_group_send(
            _group_name(user_id),
            {"type": "new_notification", "notification": nova},
            ctx=f"legacy-new user={user_id}",
        )
    return push_notification_count(user_id, count) and ok

