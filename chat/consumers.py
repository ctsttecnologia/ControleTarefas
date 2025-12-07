

# chat/consumers.py
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model


User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.user_group_name = f"notifications_{self.user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'debug',
            'message': f'✅ Notifications WebSocket conectado para usuário {self.user.username}'
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def new_message_notification(self, event):
        await self.send(text_data=json.dumps(event))

    async def new_chat_notification(self, event):
        await self.send(text_data=json.dumps(event))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        print(f"💬 ChatConsumer: Usuário {self.user.username} conectado à sala {self.room_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')

             # ✅ Verifica se o usuário está na sala
            if not await self.is_user_in_room(self.user, self.room_id):
                await self.close(code=4003)  # Código para acesso negado
                return
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'mark_as_read':
                await self.handle_mark_as_read(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
                
        except Exception as e:
            print(f"❌ Erro no WebSocket receive: {e}")

    @database_sync_to_async
    def is_user_in_room(self, user, room_id):
        """Verifica se o usuário está na sala."""
        from .models import ChatRoom
        return ChatRoom.objects.filter(id=room_id, participants=user).exists()

    async def handle_chat_message(self, data):
        """Processa mensagem de chat."""
        try:
            message_text = data.get('message', '')
            image_url = data.get('image_url', '')
            file_url = data.get('file_url', '')
            file_name = data.get('file_name', '')
            file_size = data.get('file_size', 0)
            file_type = data.get('file_type', '')
            reply_to_id = data.get('reply_to_id')

            # Salva mensagem no banco
            message_obj = await self.save_message_to_db(
                message_text, image_url, file_url, file_name, file_size, file_type, reply_to_id
            )
            
            if message_obj:
                # Cria índice de busca
                await self.create_search_index(message_obj)
                
                # Prepara dados para envio
                message_data = {
                    'type': 'chat_message',
                    'message_id': str(message_obj.id),
                    'message': message_text,
                    'image_url': image_url,
                    'file_url': file_url,
                    'file_name': file_name,
                    'file_size': message_obj.get_file_size_display() if hasattr(message_obj, 'get_file_size_display') else '',
                    'file_type': file_type,
                    'file_emoji': message_obj.get_file_type_emoji() if hasattr(message_obj, 'get_file_type_emoji') else '📄',
                    'username': self.user.username,
                    'user_id': self.user.id,
                    'timestamp': message_obj.timestamp.isoformat(),
                    'room_id': str(self.room_id),
                    'is_edited': False,
                    'reply_to': await self.get_reply_data(reply_to_id) if reply_to_id else None
                }
                
                # Envia para o grupo do chat
                await self.channel_layer.group_send(self.room_group_name, message_data)
                
        except Exception as e:
            print(f"❌ Erro ao processar mensagem: {e}")

    async def handle_mark_as_read(self, data):
        """Marca mensagem como lida."""
        try:
            message_id = data.get('message_id')
            if message_id:
                await self.mark_message_as_read(message_id)
                
                # Notifica outros usuários sobre a leitura
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_read',
                        'message_id': message_id,
                        'read_by': self.user.username,
                        'read_by_id': self.user.id
                    }
                )
        except Exception as e:
            print(f"❌ Erro ao marcar como lida: {e}")

    async def handle_typing(self, data):
        """Processa indicador de digitação."""
        try:
            is_typing = data.get('is_typing', False)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'username': self.user.username,
                    'user_id': self.user.id,
                    'is_typing': is_typing
                }
            )
        except Exception as e:
            print(f"❌ Erro no indicador de digitação: {e}")

    async def chat_message(self, event):
        """Envia mensagem para o WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            **event
        }))

    async def message_read(self, event):
        """Envia notificação de leitura."""
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            **event
        }))

    async def typing_indicator(self, event):
        """Envia indicador de digitação."""
        # Não envia para o próprio usuário
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                **event
            }))

    @database_sync_to_async
    def save_message_to_db(self, message_text, image_url, file_url, file_name, file_size, file_type, reply_to_id):
        """Salva mensagem no banco com suporte a arquivos."""
        try:
            from django.conf import settings
            from .models import ChatRoom, Message
            
            room = ChatRoom.objects.get(id=self.room_id)
            
            # Busca mensagem de resposta se especificada
            reply_to = None
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(id=reply_to_id, room=room)
                except Message.DoesNotExist:
                    pass
            
            # Cria a mensagem
            message_obj = Message.objects.create(
                room=room,
                user=self.user,
                content=message_text or '',
                reply_to=reply_to,
                file_size=file_size if file_size else None,
                file_type=file_type if file_type else None,
                original_filename=file_name if file_name else None
            )
            
            # Processa imagem
            if image_url and image_url.strip():
                image_path = self.extract_media_path(image_url, settings.MEDIA_URL)
                message_obj.image = image_path
                message_obj.save()
            
            # Processa arquivo
            if file_url and file_url.strip():
                file_path = self.extract_media_path(file_url, settings.MEDIA_URL)
                message_obj.file_attachment = file_path
                message_obj.save()
            
            # Atualiza timestamp da sala
            room.save()
            
            return message_obj
            
        except Exception as e:
            print(f"❌ Erro ao salvar mensagem: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_media_path(self, url, media_url):
        """Extrai o path relativo da URL do media."""
        if url.startswith(media_url):
            return url[len(media_url):]
        elif '/media/' in url:
            return url.split('/media/', 1)[1]
        return url

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Marca mensagem como lida."""
        try:
            from .models import Message, MessageRead
            message = Message.objects.get(id=message_id)
            MessageRead.objects.get_or_create(
                message=message,
                user=self.user
            )
        except Exception as e:
            print(f"❌ Erro ao marcar mensagem como lida: {e}")

    @database_sync_to_async
    def create_search_index(self, message):
        """Cria índice de busca para a mensagem."""
        try:
            from .models import ChatSearchIndex
            search_text = ""
            
            if message.content:
                search_text += message.content + " "
            
            if message.original_filename:
                search_text += message.original_filename
            
            if search_text.strip():
                ChatSearchIndex.objects.create(
                    message=message,
                    search_text=search_text.strip(),
                    room=message.room
                )
        except Exception as e:
            print(f"❌ Erro ao criar índice de busca: {e}")

    @database_sync_to_async
    def get_reply_data(self, reply_to_id):
        """Obtém dados da mensagem de resposta."""
        try:
            from .models import Message
            reply_msg = Message.objects.get(id=reply_to_id)
            return {
                'id': str(reply_msg.id),
                'content': reply_msg.content[:50] if reply_msg.content else None,
                'username': reply_msg.user.username,
                'has_file': bool(reply_msg.file_attachment),
                'has_image': bool(reply_msg.image)
            }
        except Exception:
            return None

    