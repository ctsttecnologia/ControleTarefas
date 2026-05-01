
# notifications/realtime.py
"""
Helpers para enviar atualizações em tempo real via WebSocket
para o NotificationConsumer.

Uso típico:
    from notifications.realtime import push_notification_count, push_new_notification
    
    push_notification_count(user)              # atualiza apenas o badge
    push_new_notification(user, notificacao)   # envia toast + atualiza badge
"""
import logging
from typing import Optional, Union

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


# ═══════════════════════════════════════════════════════════════
# Helpers internos
# ═══════════════════════════════════════════════════════════════

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
    """
    Converte uma Notificacao em dict serializável para envio via WS.
    Usa as properties do model (tempo_relativo, badge_class).
    """
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


# ═══════════════════════════════════════════════════════════════
# API pública
# ═══════════════════════════════════════════════════════════════

def push_notification_count(
    user: Union['User', int, None],
    count: Optional[int] = None,
) -> bool:
    """
    Envia a contagem de notificações não lidas via WebSocket.
    Atualiza o badge do sino em tempo real.

    Args:
        user: instância de User OU user_id (int)
        count: contagem opcional pré-calculada. Se None, calcula do banco.

    Returns:
        True se o evento foi enviado com sucesso, False caso contrário.
    """
    user_id = _resolve_user_id(user)
    if user_id is None:
        logger.debug("push_notification_count: user inválido (%r)", user)
        return False

    # Calcula contagem se não foi passada
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
        logger.warning("Channel layer não configurado — push ignorado")
        return False

    try:
        async_to_sync(channel_layer.group_send)(
            _group_name(user_id),
            {
                'type': 'notification_count_update',  # → handler do consumer
                'count': int(count),
            },
        )
        logger.debug(
            "📡 Push contagem: user=%s count=%s", user_id, count,
        )
        return True
    except Exception as e:
        logger.exception(
            "Erro no push de contagem (user=%s): %s", user_id, e,
        )
        return False


def push_new_notification(user, notificacao) -> bool:
    """
    Envia uma nova notificação completa (para toast/popup) +
    atualiza o badge.

    Args:
        user: instância de User (ou user_id)
        notificacao: instância de Notificacao

    Returns:
        True se enviou com sucesso.
    """
    user_id = _resolve_user_id(user)
    if user_id is None:
        return False

    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("Channel layer não configurado — push ignorado")
        return False

    try:
        # 1) Evento de "nova notificação" (para toast/popup no front)
        payload = _serialize_notificacao(notificacao)
        async_to_sync(channel_layer.group_send)(
            _group_name(user_id),
            {
                'type': 'new_notification',  # → handler do consumer
                'notification': payload,
            },
        )

        # 2) Atualiza badge (recalcula do banco para garantir consistência)
        push_notification_count(user_id)

        logger.debug(
            "📡 Push nova notificação: user=%s notif=%s tipo=%s",
            user_id, notificacao.pk, notificacao.tipo,
        )
        return True

    except Exception as e:
        logger.exception(
            "Erro no push de nova notificação (user=%s, notif=%s): %s",
            user_id, getattr(notificacao, 'pk', '?'), e,
        )
        return False


def push_notification_read(user, notificacao_id: int) -> bool:
    """
    Notifica o cliente que uma notificação foi marcada como lida
    (útil para sincronizar múltiplas abas/dispositivos).

    Args:
        user: instância de User (ou user_id)
        notificacao_id: ID da notificação lida

    Returns:
        True se enviou com sucesso.
    """
    user_id = _resolve_user_id(user)
    if user_id is None:
        return False

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return False

    try:
        async_to_sync(channel_layer.group_send)(
            _group_name(user_id),
            {
                'type': 'notification_read',  # → handler do consumer
                'notification_id': notificacao_id,
            },
        )
        # Atualiza badge também
        push_notification_count(user_id)
        return True
    except Exception as e:
        logger.exception(
            "Erro no push de notificação lida (user=%s): %s", user_id, e,
        )
        return False


