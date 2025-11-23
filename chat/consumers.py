
# chat/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, Message, User  # Importe seus models

# =================================================================
# 1. NOTIFICATION CONSUMER (O que você já fez - Mantenha assim)
# =================================================================
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.user_group_name = f"notifications_{self.user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()
        
        # DEBUG: Envia mensagem de teste ao conectar
        await self.send(text_data=json.dumps({
            'type': 'debug',
            'message': f'✅ Notifications WebSocket conectado para usuário {self.user.username}'
        }))
        print(f"🔔 NotificationConsumer: Usuário {self.user.username} conectado ao grupo {self.user_group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        print(f"🔔 NotificationConsumer: Usuário {self.user.username if self.user.is_authenticated else 'Anônimo'} desconectado")

    async def new_message_notification(self, event):
        print(f"🔔 ENVIANDO NOTIFICAÇÃO para {self.user.username}: {event}")
        await self.send(text_data=json.dumps(event))

    async def new_chat_notification(self, event):
        print(f"🔔 NOVO CHAT para {self.user.username}: {event}")
        await self.send(text_data=json.dumps(event))


# =================================================================
# 2. CHAT CONSUMER (É AQUI QUE VOCÊ APLICA O CÓDIGO DE ENVIO)
# =================================================================
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        print(f"💬 ChatConsumer: Usuário {self.user.username} conectado à sala {self.room_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        print(f"💬 ChatConsumer: Usuário {self.user.username} desconectado da sala {self.room_id}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_content = data.get('message', '')
            
            print(f"💬 Mensagem recebida de {self.user.username}: {message_content}")
            
            # Salva a mensagem no banco
            message = await self.save_message(message_content)
            
            # Prepara dados para notificação
            room = await self.get_room()
            participants = await self.get_room_participants()
            
            # Envia para a sala de chat
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_content,
                    'username': self.user.username,
                    'timestamp': message.timestamp.isoformat(),
                    'user_id': str(self.user.id)
                }
            )
            
            # ENVIA NOTIFICAÇÕES PARA TODOS OS PARTICIPANTES (exceto o remetente)
            for participant in participants:
                if participant.id != self.user.id:
                    await self.send_notification_to_user(participant, message, room)
                    
        except Exception as e:
            print(f"❌ Erro no receive: {e}")

    async def send_notification_to_user(self, participant, message, room):
        """Envia notificação para um usuário específico"""
        try:
            # Prepara o avatar
            avatar_url = await self.get_user_avatar(self.user)
            
            notification_data = {
                'type': 'new_message',
                'room_id': str(room.id),
                'message_id': str(message.id),
                'sender_id': str(self.user.id),
                'sender_username': self.user.username,
                'sender_name': self.user.get_full_name() or self.user.username,
                'avatar_url': avatar_url,
                'message_content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'room_name': room.name
            }
            
            print(f"🔔 Enviando notificação para {participant.username}: {notification_data}")
            
            # Envia para o grupo de notificações do usuário
            await self.channel_layer.group_send(
                f"notifications_{participant.id}",
                {
                    'type': 'new_message_notification',
                    **notification_data
                }
            )
            
        except Exception as e:
            print(f"❌ Erro ao enviar notificação para {participant.username}: {e}")

    async def chat_message(self, event):
        """Envia mensagem para o WebSocket do chat"""
        await self.send(text_data=json.dumps(event))

    # ========== MÉTODOS DE BANCO DE DADOS ==========
    
    @database_sync_to_async
    def save_message(self, content):
        from .models import ChatRoom, Message
        room = ChatRoom.objects.get(id=self.room_id)
        return Message.objects.create(
            user=self.user, 
            room=room, 
            content=content
        )

    @database_sync_to_async
    def get_room(self):
        from .models import ChatRoom
        return ChatRoom.objects.get(id=self.room_id)

    @database_sync_to_async
    def get_room_participants(self):
        from .models import ChatRoom
        room = ChatRoom.objects.get(id=self.room_id)
        return list(room.participants.all())

    @database_sync_to_async
    def get_user_avatar(self, user):
        """Obtém a URL do avatar do usuário"""
        try:
            if hasattr(user, 'profile') and user.profile.avatar:
                return user.profile.avatar.url
        except Exception as e:
            print(f"⚠️ Erro ao obter avatar: {e}")
        return '/static/images/default-avatar.png'
    
    