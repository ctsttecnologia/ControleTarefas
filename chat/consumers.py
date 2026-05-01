# chat/consumers.py
"""
WebSocket Consumers do app de Chat.

Consumers:
- NotificationConsumer: notificações em tempo real do usuário (badge, novos chats)
- ChatConsumer: mensagens de chat em uma sala específica
"""
import json
import logging
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from .utils import sanitize_message, validate_message_content
from .validators import validate_uploaded_file


User = get_user_model()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION CONSUMER
# ═══════════════════════════════════════════════════════════════

class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumer de notificações por usuário.

    Cada usuário autenticado entra em um grupo `notifications_<user_id>`,
    e recebe eventos de:
        - new_message_notification     → nova mensagem em qualquer chat
        - new_chat_notification        → nova sala/conversa criada
        - notification_count_update    → atualização do badge de contagem
    """

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        self.user_group_name = f"notifications_{self.user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

        logger.info(
            "NotificationConsumer conectado: user=%s group=%s",
            self.user.username, self.user_group_name,
        )

        # Envia contagem inicial de notificações não lidas ao conectar
        try:
            count = await self.get_unread_count()
            await self.send(text_data=json.dumps({
                'type': 'notification_count_update',
                'count': count,
            }))
        except Exception as e:
            logger.exception("Erro ao enviar contagem inicial: %s", e)

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name, self.channel_name,
            )
            logger.info(
                "NotificationConsumer desconectado: user=%s code=%s",
                getattr(self.user, 'username', '?'), close_code,
            )

    # ───── Handlers de eventos do channel layer ─────

    async def new_message_notification(self, event):
        """Recebe evento de nova mensagem e repassa ao cliente."""
        await self.send(text_data=json.dumps(event))

    async def new_chat_notification(self, event):
        """Recebe evento de nova conversa criada."""
        await self.send(text_data=json.dumps(event))

    async def notification_count_update(self, event):
        """Recebe atualização do contador de notificações (push)."""
        await self.send(text_data=json.dumps({
            'type': 'notification_count_update',
            'count': event.get('count', 0),
        }))

    async def new_message_notification(self, event):
        """[LEGADO] Mantido para compatibilidade."""
        await self.send(text_data=json.dumps(event))

    async def new_chat_notification(self, event):
        """Nova sala/conversa criada."""
        await self.send(text_data=json.dumps(event))

    async def notification_count_update(self, event):
        """Atualização do badge (push de contagem)."""
        await self.send(text_data=json.dumps({
            'type': 'notification_count_update',
            'count': event.get('count', 0),
        }))

    # Novos handlers
    async def new_notification(self, event):
        """Nova notificação criada (envia toast + dados completos)."""
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event.get('notification', {}),
        }))

    async def notification_read(self, event):
        """Notificação marcada como lida (sincroniza outras abas)."""
        await self.send(text_data=json.dumps({
            'type': 'notification_read',
            'notification_id': event.get('notification_id'),
        }))

    # ───── DB helpers ─────

    @database_sync_to_async
    def get_unread_count(self):
        """Conta notificações não lidas do usuário."""
        try:
            from notifications.models import Notificacao
            return Notificacao.objects.filter(
                usuario=self.user, lida=False,
            ).count()
        except Exception as e:
            logger.exception("Erro ao contar não lidas: %s", e)
            return 0


# ═══════════════════════════════════════════════════════════════
# CHAT CONSUMER
# ═══════════════════════════════════════════════════════════════

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consumer de uma sala de chat específica.

    Mensagens recebidas:
        - chat_message    → texto
        - file_message    → arquivo/imagem
        - typing          → indicador de digitação
        - mark_as_read    → marcar mensagem como lida
    """

    RATE_LIMIT_MAX_MESSAGES = 60        # 60 msgs/min
    RATE_LIMIT_WINDOW_SECONDS = 60

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        if not await self.is_user_in_room(self.user, self.room_id):
            logger.warning(
                "Acesso negado à sala %s para user=%s",
                self.room_id, self.user.username,
            )
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        logger.info(
            "ChatConsumer conectado: user=%s room=%s",
            self.user.username, self.room_id,
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name,
            )
            logger.info(
                "ChatConsumer desconectado: user=%s room=%s code=%s",
                getattr(self.user, 'username', '?'),
                getattr(self, 'room_id', '?'),
                close_code,
            )

    # ───── Recebe mensagens do cliente ─────

    async def receive(self, text_data):
        """Despacha mensagens recebidas pelo tipo."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as e:
            logger.warning("JSON inválido recebido: %s", e)
            await self._send_error('Dados inválidos (JSON malformado)')
            return

        message_type = data.get('type', 'chat_message')

        # Rate limiting
        if not await self.check_rate_limit():
            await self._send_error('Muitas mensagens. Aguarde alguns segundos.')
            return

        try:
            handlers = {
                'chat_message': self.handle_chat_message,
                'file_message': self.handle_file_message,
                'typing': self.handle_typing,
                'mark_as_read': self.handle_mark_as_read,
            }
            handler = handlers.get(message_type)

            if handler is None:
                logger.warning("Tipo de mensagem desconhecido: %s", message_type)
                await self._send_error(f'Tipo desconhecido: {message_type}')
                return

            await handler(data)

        except Exception as e:
            logger.exception("❌ Erro processando mensagem (%s): %s", message_type, e)
            await self._send_error('Erro interno ao processar mensagem')

    # ───── Handlers por tipo ─────

    async def handle_chat_message(self, data):
        """Processa e salva mensagem de texto."""
        message_text = data.get('message', '').strip()

        # 1 Valida vazio
        if not message_text:
            logger.debug("Mensagem vazia ignorada")
            return

        # 2️ Valida conteúdo
        is_valid, error = validate_message_content(message_text)
        if not is_valid:
            await self._send_error(error)
            return

        # 3️ Sanitiza
        sanitized = sanitize_message(message_text)

        # 4️ Salva (UMA VEZ SÓ!)
        message_obj = await self.save_message_to_db(sanitized)
        if not message_obj:
            await self._send_error('Falha ao salvar mensagem')
            return

        # 5️ Broadcast
        message_data = {
            'type': 'chat_message',
            'message_id': str(message_obj.id),
            'message': sanitized,
            'message_type': 'text',
            'username': self.user.get_full_name() or self.user.username,
            'user_id': self.user.id,
            'timestamp': message_obj.timestamp.isoformat(),
            'room_id': str(self.room_id),
        }

        await self.channel_layer.group_send(self.room_group_name, message_data)
        logger.info(
            "Mensagem enviada: room=%s user=%s id=%s",
            self.room_id, self.user.username, message_obj.id,
        )

    async def handle_file_message(self, data):
        """Processa mensagem com arquivo/imagem."""
        file_data = data.get('file_data') or {}

        if not file_data:
            logger.warning("file_data vazio")
            await self._send_error('Dados do arquivo ausentes')
            return

        file_name = file_data.get('name', 'arquivo')
        logger.info(
            "Processando arquivo: name=%s user=%s room=%s",
            file_name, self.user.username, self.room_id,
        )

        message_obj = await self.save_file_message_to_db(file_data)
        if not message_obj:
            await self._send_error('Falha ao salvar arquivo')
            return

        message_data = {
            'type': 'chat_message',
            'message_id': str(message_obj.id),
            'message': '',
            'message_type': 'file',
            'file_data': file_data,
            'username': self.user.get_full_name() or self.user.username,
            'user_id': self.user.id,
            'timestamp': message_obj.timestamp.isoformat(),
            'room_id': str(self.room_id),
        }

        await self.channel_layer.group_send(self.room_group_name, message_data)
        logger.info("Arquivo enviado: id=%s", message_obj.id)

    async def handle_typing(self, data):
        """Indicador de digitação."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'username': self.user.username,
                'user_id': self.user.id,
                'is_typing': bool(data.get('is_typing', False)),
            },
        )

    async def handle_mark_as_read(self, data):
        """Marca mensagem como lida."""
        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_as_read(message_id)

    # ───── Handlers de eventos do channel layer ─────

    async def chat_message(self, event):
        """Envia mensagem do grupo para o WebSocket do cliente."""
        event_copy = dict(event)
        event_copy['is_own'] = (event.get('user_id') == self.user.id)

        await self.send(text_data=json.dumps({
            'type': 'new_message',
            **event_copy,
        }))

    async def typing_indicator(self, event):
        """Envia indicador de digitação (exceto pro próprio usuário)."""
        if event.get('user_id') == self.user.id:
            return

        await self.send(text_data=json.dumps({
            'type': 'typing',
            **event,
        }))

    # ───── Helpers ─────

    async def _send_error(self, message: str):
        """Envia mensagem de erro padronizada ao cliente."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
        }))

    # ───── Database operations ─────

    @database_sync_to_async
    def is_user_in_room(self, user, room_id):
        """Verifica se o usuário pertence à sala."""
        from .models import ChatRoom
        return ChatRoom.objects.filter(id=room_id, participants=user).exists()

    @database_sync_to_async
    def save_message_to_db(self, message_text):
        """Salva mensagem de texto no banco."""
        try:
            from .models import ChatRoom, Message

            room = ChatRoom.objects.get(id=self.room_id)
            message_obj = Message.objects.create(
                room=room,
                user=self.user,
                content=message_text,
            )

            room.updated_at = timezone.now()
            room.save(update_fields=['updated_at'])

            logger.debug("Mensagem salva: id=%s", message_obj.id)
            return message_obj

        except Exception as e:
            logger.exception("Erro ao salvar mensagem: %s", e)
            return None

    @database_sync_to_async
    def save_file_message_to_db(self, file_data):
        """Salva mensagem com arquivo no banco."""
        try:
            from .models import ChatRoom, Message

            room = ChatRoom.objects.get(id=self.room_id)

            file_url = file_data.get('url', '')
            file_name = file_data.get('name', 'arquivo')
            file_size = file_data.get('size', 0)
            file_type = file_data.get('type', 'application/octet-stream')

            is_image = file_type.startswith('image/')

            message_obj = Message.objects.create(
                room=room,
                user=self.user,
                content='',
                original_filename=file_name,
                file_size=file_size,
                file_type=file_type,
            )

            # Remove prefixos de mídia da URL para salvar caminho relativo
            relative_path = self._strip_media_prefix(file_url)

            if is_image:
                message_obj.image = relative_path
            else:
                message_obj.file_attachment = relative_path

            message_obj.save()

            room.updated_at = timezone.now()
            room.save(update_fields=['updated_at'])

            logger.debug(
                "Arquivo salvo: id=%s image=%s file=%s",
                message_obj.id, message_obj.image, message_obj.file_attachment,
            )
            return message_obj

        except Exception as e:
            logger.exception("Erro ao salvar arquivo: %s", e)
            return None

    @staticmethod
    def _strip_media_prefix(url: str) -> str:
        """Remove prefixos /midia/ ou /media/ para obter caminho relativo."""
        if not url:
            return ''
        for prefix in ('/midia/', '/media/'):
            if url.startswith(prefix):
                return url[len(prefix):]
        return url

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Registra leitura de mensagem."""
        try:
            from .models import Message, MessageRead
            message = Message.objects.get(id=message_id)
            MessageRead.objects.get_or_create(
                message=message,
                user=self.user,
            )
        except Exception as e:
            logger.exception("Erro ao marcar como lida: %s", e)

    @database_sync_to_async
    def check_rate_limit(self):
        """
        Rate limit: máx N mensagens por janela de tempo, por usuário.
        
        Implementação atômica usando cache.add + cache.incr para evitar
        race conditions em ambientes multi-worker.
        """
        cache_key = f"ws_rate_{self.user.id}"

        # Tenta criar contador novo (atômico)
        added = cache.add(cache_key, 1, timeout=self.RATE_LIMIT_WINDOW_SECONDS)
        if added:
            return True

        # Já existia → incrementa atomicamente
        try:
            count = cache.incr(cache_key)
        except ValueError:
            # Chave expirou entre add e incr — recria
            cache.set(cache_key, 1, timeout=self.RATE_LIMIT_WINDOW_SECONDS)
            return True

        return count <= self.RATE_LIMIT_MAX_MESSAGES
