# chat/consumers.py
"""
WebSocket Consumers do app de Chat.

- NotificationConsumer: eventos do usuário (badge, novas mensagens/salas)
- ChatConsumer: mensagens de uma sala específica
"""
import json
import logging
import time
from collections import deque

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .utils import sanitize_message, validate_message_content

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION CONSUMER
# ═══════════════════════════════════════════════════════════════

class NotificationConsumer(AsyncWebsocketConsumer):
    """Grupo `notifications_<user_id>`: badge, toasts, novas mensagens/salas."""

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        self.user_group_name = f'notifications_{self.user.id}'
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

        count = await self.get_unread_count()
        await self._send({'type': 'notification_count_update', 'count': count})

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name, self.channel_name,
            )

    async def _send(self, payload):
        await self.send(text_data=json.dumps(payload))

    # ── eventos do channel layer ──
    async def new_message_notification(self, event):
        await self._send(event)

    async def new_chat_notification(self, event):
        await self._send(event)

    async def notification_count_update(self, event):
        await self._send({
            'type': 'notification_count_update',
            'count': event.get('count', 0),
        })

    async def new_notification(self, event):
        await self._send({
            'type': 'new_notification',
            'notification': event.get('notification', {}),
        })

    async def notification_read(self, event):
        await self._send({
            'type': 'notification_read',
            'notification_id': event.get('notification_id'),
        })

    async def chat_room_read(self, event):
        """Sala lida em outra aba/dispositivo → zera só o badge daquela sala."""
        await self._send({'type': 'chat_room_read', 'room_id': event['room_id']})

    @database_sync_to_async
    def get_unread_count(self):
        from notifications.models import Notificacao
        return Notificacao.objects.filter(usuario=self.user, lida=False).count()


# ═══════════════════════════════════════════════════════════════
# CHAT CONSUMER
# ═══════════════════════════════════════════════════════════════

class ChatConsumer(AsyncWebsocketConsumer):
    # mark_as_read e typing ficam fora do limite
    RATE_LIMITED_TYPES = frozenset({'chat_message', 'file_message'})
    RATE_LIMIT_MAX = 20       # eventos
    RATE_LIMIT_WINDOW = 10    # por N segundos
    FILE_KEYS = ('name', 'url', 'type', 'size')  # únicos campos repassados ao grupo

    async def chat_message(self, event):
        logger.info('chat_message → user=%s msg=%s', self.user.id, event.get('message_id'))
    
    # ───── ciclo de vida ─────

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        self._rate_hits = deque()

        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        if not await self.is_user_in_room():
            logger.warning(
                'Acesso negado à sala %s para user=%s',
                self.room_id, self.user.username,
            )
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info('ChatConsumer conectado: user=%s room=%s', self.user.username, self.room_id)

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name,
            )
            logger.info(
                'ChatConsumer desconectado: user=%s room=%s code=%s',
                getattr(self.user, 'username', '?'), self.room_id, close_code,
            )

    # ───── entrada do cliente ─────

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error('Dados inválidos (JSON malformado)')
            return
        if not isinstance(data, dict):
            await self._send_error('Formato inválido')
            return

        message_type = data.get('type', 'chat_message')

        if message_type in self.RATE_LIMITED_TYPES and not self.check_rate_limit():
            await self._send_error('Muitas mensagens. Aguarde um instante.')
            return

        handlers = {
            'chat_message': self.handle_chat_message,
            'file_message': self.handle_file_message,
            'typing': self.handle_typing,
            'mark_as_read': self.handle_mark_as_read,
        }
        handler = handlers.get(message_type)
        if handler is None:
            await self._send_error(f'Tipo desconhecido: {message_type}')
            return

        try:
            await handler(data)
        except Exception:
            logger.exception('Erro processando mensagem (%s)', message_type)
            await self._send_error('Erro interno ao processar mensagem')

    # ───── handlers por tipo ─────

    async def handle_chat_message(self, data):
        text = str(data.get('message', '')).strip()
        if not text:
            return

        is_valid, error = validate_message_content(text)
        if not is_valid:
            await self._send_error(error)
            return

        sanitized = sanitize_message(text)

        msg = await self.save_message_to_db(sanitized)
        if not msg:
            await self._send_error('Falha ao salvar mensagem')
            return

        await self._broadcast(msg, message=sanitized, message_type='text')
        await self._notify_recipients(msg, sanitized)

    async def handle_file_message(self, data):
        raw = data.get('file_data')
        if not isinstance(raw, dict) or not raw.get('url'):
            await self._send_error('Dados do arquivo ausentes')
            return

        file_data = {k: raw.get(k) for k in self.FILE_KEYS if k in raw}

        msg = await self.save_file_message_to_db(file_data)
        if not msg:
            await self._send_error('Falha ao salvar arquivo')
            return

        await self._broadcast(msg, message='', message_type='file', file_data=file_data)
        await self._notify_recipients(msg, f"📎 {file_data.get('name') or 'Arquivo'}")

    async def handle_typing(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'typing_indicator',
            'username': self.user.username,
            'user_id': self.user.id,
            'is_typing': bool(data.get('is_typing', False)),
        })

    async def handle_mark_as_read(self, data):
        """`all: true` marca a sala toda; `message_id` marca uma mensagem."""
        if data.get('all'):
            count = await self.mark_all_room_messages_as_read()
            # avisa as outras abas/dispositivos do usuário
            await self.channel_layer.group_send(
                f'notifications_{self.user.id}',
                {'type': 'chat_room_read', 'room_id': str(self.room_id)},
            )
            await self.send(text_data=json.dumps({
                'type': 'read_receipt',
                'room_id': str(self.room_id),
                'marked': count,
            }))
            return

        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_as_read(message_id)

    # ───── eventos do channel layer ─────
    # O 'type' do evento é o nome do handler; o 'type' enviado ao cliente
    # precisa sobrescrever por último, senão o front recebe o nome do handler.

    async def chat_message(self, event):
        payload = {k: v for k, v in event.items()}
        payload['type'] = 'new_message'
        payload['is_own'] = event.get('user_id') == self.user.id
        await self.send(text_data=json.dumps(payload))

    async def typing_indicator(self, event):
        if event.get('user_id') == self.user.id:
            return
        payload = dict(event)
        payload['type'] = 'typing'
        await self.send(text_data=json.dumps(payload))

    # ───── helpers ─────

    def check_rate_limit(self):
        """Janela deslizante em memória (por conexão). Síncrono: sem ORM, sem I/O."""
        now = time.monotonic()
        hits = self._rate_hits
        while hits and now - hits[0] > self.RATE_LIMIT_WINDOW:
            hits.popleft()
        if len(hits) >= self.RATE_LIMIT_MAX:
            return False
        hits.append(now)
        return True

    async def _send_error(self, message):
        # 'message' e 'error' para compatibilizar com qualquer leitura no front
        await self.send(text_data=json.dumps({
            'type': 'error', 'message': message, 'error': message,
        }))

    async def _broadcast(self, msg, **extra):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'chat_message',
            'message_id': str(msg.id),
            'username': self.user.get_full_name() or self.user.username,
            'user_id': self.user.id,
            'timestamp': msg.timestamp.isoformat(),
            'room_id': str(self.room_id),
            **extra,
        })

    async def _notify_recipients(self, msg, preview):
        """Avisa os outros participantes (badge/som), mesmo sem a sala aberta."""
        try:
            ids = await self.get_recipient_ids()
            payload = {
                'type': 'new_message_notification',
                'room_id': str(self.room_id),
                'message_id': str(msg.id),
                'sender': self.user.get_full_name() or self.user.username,
                'sender_id': self.user.id,
                'preview': (preview or '')[:100],
                'timestamp': msg.timestamp.isoformat(),
            }
            for uid in ids:
                await self.channel_layer.group_send(f'notifications_{uid}', payload)
        except Exception:
            # a mensagem já foi salva e entregue; falha aqui não pode derrubar o fluxo
            logger.exception('Falha ao notificar destinatários')

    @staticmethod
    def _strip_media_prefix(url):
        for prefix in ('/midia/', '/media/'):
            if url.startswith(prefix):
                return url[len(prefix):]
        return url

    # ───── banco de dados ─────

    @database_sync_to_async
    def is_user_in_room(self):
        from .models import ChatRoom
        return ChatRoom.objects.filter(id=self.room_id, participants=self.user).exists()

    @database_sync_to_async
    def get_recipient_ids(self):
        from .models import ChatRoom
        room = ChatRoom.objects.filter(id=self.room_id).first()
        if not room:
            return []
        return list(room.participants.exclude(id=self.user.id).values_list('id', flat=True))

    @database_sync_to_async
    def save_message_to_db(self, text):
        from .models import ChatRoom, Message
        try:
            msg = Message.objects.create(room_id=self.room_id, user=self.user, content=text)
            ChatRoom.objects.filter(id=self.room_id).update(updated_at=timezone.now())
            return msg
        except Exception:
            logger.exception('Erro ao salvar mensagem')
            return None

    @database_sync_to_async
    def save_file_message_to_db(self, file_data):
        from .models import ChatRoom, Message
        try:
            path = self._strip_media_prefix(str(file_data.get('url', '')))
            if not path or '..' in path or path.startswith(('/', 'http')):
                logger.warning('Caminho de arquivo inválido: %r', path)
                return None

            file_type = file_data.get('type') or 'application/octet-stream'
            extra = {'image': path} if file_type.startswith('image/') else {'file_attachment': path}

            msg = Message.objects.create(
                room_id=self.room_id,
                user=self.user,
                content='',
                original_filename=file_data.get('name') or 'arquivo',
                file_size=file_data.get('size') or 0,
                file_type=file_type,
                **extra,
            )
            ChatRoom.objects.filter(id=self.room_id).update(updated_at=timezone.now())
            return msg
        except Exception:
            logger.exception('Erro ao salvar arquivo')
            return None

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        from .models import Message, MessageRead
        try:
            msg = (
                Message.objects.filter(id=message_id, room_id=self.room_id)
                .exclude(user=self.user)
                .first()
            )
            if msg:
                MessageRead.objects.get_or_create(message=msg, user=self.user)
        except Exception:
            logger.exception('Erro em mark_message_as_read')

    @database_sync_to_async
    def mark_all_room_messages_as_read(self):
        from .models import Message, MessageRead
        try:
            pending = (
                Message.objects.filter(room_id=self.room_id)
                .exclude(user=self.user)
                .exclude(message_reads__user=self.user)
                .values_list('pk', flat=True)
            )
            reads = [MessageRead(message_id=pk, user=self.user) for pk in pending]
            if reads:
                MessageRead.objects.bulk_create(reads, ignore_conflicts=True)
            logger.info(
                'Bulk read: room=%s user=%s marcadas=%s',
                self.room_id, self.user.username, len(reads),
            )
            return len(reads)
        except Exception:
            logger.exception('Erro em mark_all_room_messages_as_read')
            return 0

