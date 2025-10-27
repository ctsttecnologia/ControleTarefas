
# chat/consumers.py
import json
import base64 # Para decodificar a imagem
import uuid   # Para nomes de arquivo de imagem
from django.core.files.base import ContentFile # Para salvar a imagem
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatMessage, ChatRoom

User = get_user_model() # Pega o seu modelo de usuário personalizado

class ChatConsumer(AsyncWebsocketConsumer):

    # Chamado quando o cliente se conecta
    async def connect(self):
        # Pega o ID da sala pela URL
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # Pega o usuário (graças ao AuthMiddlewareStack)
        self.user = self.scope['user']

        # Rejeita conexão se o usuário não estiver logado
        if self.user.is_anonymous:
            await self.close()
            return

        # Carrega a sala e verifica permissões
        self.room = await self.get_room(self.room_id)

        if not self.room or not await self.is_user_participant(self.room, self.user):
            await self.close() # Fecha a conexão se não tiver permissão
            return

        # Entra no grupo (sala de chat)
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Aceita a conexão
        await self.accept()

    # Chamado quando o cliente se desconecta
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'): # Garante que o grupo existe antes de sair
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Chamado quando o servidor recebe uma mensagem do cliente (JS)
    async def receive(self, text_data):
        json_data = json.loads(text_data)
        message_type = json_data.get('type')

        # Se for uma mensagem de texto
        if message_type == 'chat_message':
            message_content = json_data.get('message', '')
            if message_content.strip(): # Só salva se tiver conteúdo de texto
                saved_message = await self.save_message(message_content=message_content)

                # Envia para o grupo
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'send_chat_message', # Nome da função 'handler'
                        'message': message_content,
                        'username': self.user.username,
                        'timestamp': saved_message.timestamp.isoformat(),
                        'message_id': str(saved_message.id)
                    }
                )

        # Se for uma mensagem de imagem
        elif message_type == 'image_message':
            image_data_base64 = json_data.get('image') # Ex: "data:image/png;base64,iVBORw0..."
            if image_data_base64:
                # Salva a imagem
                saved_message = await self.save_image_message(image_data_base64)
                if saved_message:
                    # Envia para o grupo
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'send_chat_message',
                            'image_url': saved_message.get_image_url(), # Envia a URL da imagem
                            'username': self.user.username,
                            'timestamp': saved_message.timestamp.isoformat(),
                            'message_id': str(saved_message.id)
                        }
                    )
        # Emojis são tratados como 'chat_message' (texto)


    # Função "Handler" chamada pelo group_send
    async def send_chat_message(self, event):
        # Esta função é chamada para CADA cliente no grupo
        message = event.get('message')
        image_url = event.get('image_url')
        username = event['username']
        timestamp = event['timestamp']
        message_id = event['message_id']

        # Envia a mensagem de volta para o cliente (JS)
        await self.send(text_data=json.dumps({
            'message': message,
            'image_url': image_url,
            'username': username,
            'timestamp': timestamp,
            'message_id': message_id,
        }))

    # --- Funções Helper Assíncronas ---
    # Usamos @sync_to_async para falar com o BD (que é síncrono)

    @sync_to_async
    def get_room(self, room_id):
        try:
            # Usamos UUID para buscar o ID da sala
            return ChatRoom.objects.get(id=uuid.UUID(room_id))
        except (ChatRoom.DoesNotExist, ValueError):
            return None

    @sync_to_async
    def is_user_participant(self, room, user):
        return room.is_participant(user)

    @sync_to_async
    def save_message(self, message_content):
        return ChatMessage.objects.create(
            room=self.room,
            user=self.user,
            content=message_content
        )

    @sync_to_async
    def save_image_message(self, image_data_base64):
        try:
            # Separa o cabeçalho (ex: "data:image/png;base64,") do conteúdo
            format, imgstr = image_data_base64.split(';base64,') 
            ext = format.split('/')[-1] # Ex: png, jpeg

            # Cria um nome de arquivo único
            file_name = f"{uuid.uuid4()}.{ext}"

            # Decodifica e salva a imagem
            data = ContentFile(base64.b64decode(imgstr), name=file_name)

            message = ChatMessage.objects.create(
                room=self.room,
                user=self.user,
                image=data
            )
            return message
        except Exception as e:
            print(f"Erro ao salvar imagem: {e}")
            return None
