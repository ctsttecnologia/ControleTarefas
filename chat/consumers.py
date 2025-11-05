
# chat/consumers.py
# chat/consumers.py
import json
import base64
from django.core.files.base import ContentFile
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

# =================================================================
# 1. CONSUMER DE NOTIFICAÇÕES (NOVO)
# Este consumer lida com notificações GERAIS para um usuário.
# (Ex: "Você foi adicionado a um novo chat")
# =================================================================
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
            
        # Cada usuário logado entra em seu próprio grupo de notificação
        self.user_group_name = f"notifications_{self.user.id}"

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"✅ Notificação WebSocket conectada para usuário {self.user.id}")

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        print(f"🔴 Notificação WebSocket desconectada para usuário {self.user.id}")

    # Chamado pelas views quando um NOVO CHAT é criado
    async def new_chat_notification(self, event):
        """ Envia dados de uma nova sala de chat para o cliente. """
        await self.send(text_data=json.dumps({
            'type': 'new_chat',
            'room': event['room']
        }))

    # Chamado pelo ChatConsumer quando uma NOVA MENSAGEM chega
    async def new_message_notification(self, event):
        """ Envia uma notificação de nova mensagem. """
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'room_id': event['room_id'],
            'sender_username': event['sender_username']
        }))

# =================================================================
# 2. CONSUMER DE CHAT (ATUALIZADO)
# Este consumer lida com mensagens DENTRO de uma sala específica.
# =================================================================
class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user'] 

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        is_participant = await self.is_user_participant(self.room_id, self.user)
        if not is_participant:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"✅✅✅ CHAT CONECTADO: Usuário {self.user.username} à sala {self.room_id}")

    async def disconnect(self, close_code):
        print(f"🔴 CHAT DESCONECTADO: Sala {self.room_id} - Código: {close_code}")
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_content = data.get('message', '')
            image_data_str = data.get('image', None)

            if not message_content and not image_data_str:
                return # Ignora envios vazios

            message = await self.save_message(
                room_id=self.room_id,
                user=self.user,
                content=message_content,
                image_data_str=image_data_str
            )
            if message is None: return

            # Prepara dados para enviar ao GRUPO DA SALA
            response_data = {
                'type': 'chat_message', # Chama a função 'chat_message'
                'message': message.content,
                'username': self.user.username,
                'timestamp': message.timestamp.isoformat(),
                'image_url': message.image.url if message.image else None
            }
            await self.channel_layer.group_send(
                self.room_group_name,
                response_data
            )
            
            # ✅ NOVO: Envia notificação para os canais pessoais dos outros usuários
            other_participants = await self.get_other_participants(self.room_id, self.user)
            for user_id in other_participants:
                await self.channel_layer.group_send(
                    f"notifications_{user_id}", # Grupo de notificação pessoal
                    {
                        'type': 'new_message_notification', # Chama 'new_message_notification' no NotificationConsumer
                        'room_id': self.room_id,
                        'sender_username': self.user.username
                    }
                )

        except Exception as e:
            print(f"❌ Erro ao processar mensagem: {e}")

    async def chat_message(self, event):
        """ Envia a mensagem formatada para o cliente WebSocket """
        await self.send(text_data=json.dumps({
            'message': event.get('message'),
            'username': event.get('username'),
            'timestamp': event.get('timestamp'),
            'image_url': event.get('image_url')
        }))

    # --- Funções Auxiliares de Banco de Dados ---

    @sync_to_async
    def is_user_participant(self, room_id, user):
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(id=room_id)
            print(f"🏠 Sala encontrada: {room.name}")
            return room.participants.filter(id=user.id).exists()
        except Exception as e:
            print(f"❌ Erro verificação participante: {e}")
            return False

    @sync_to_async
    def get_other_participants(self, room_id, sender_user):
        """ Pega os IDs de todos os participantes, EXCETO o remetente. """
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(id=room_id)
            return list(
                room.participants.exclude(id=sender_user.id).values_list('id', flat=True)
            )
        except ChatRoom.DoesNotExist:
            return []

    @sync_to_async
    def save_message(self, room_id, user, content, image_data_str=None):
        from .models import ChatRoom, Message
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            
            image_file = None
            if image_data_str:
                try:
                    format, imgstr = image_data_str.split(';base64,') 
                    ext = format.split('/')[-1] 
                    image_file = ContentFile(base64.b64decode(imgstr), name=f'img_{user.id}_{room_id}.{ext}')
                except Exception as e:
                    print(f"❌ Erro ao decodificar imagem Base64: {e}")
            
            message = Message.objects.create(
                room=room,
                user=user,
                content=content if content else "",
                image=image_file
            )
            print(f"💾 Mensagem salva no banco: {message.id}")
            return message
        except Exception as e:
            print(f"❌ Erro ao salvar mensagem: {e}")
            return None