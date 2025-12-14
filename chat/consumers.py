

# chat/consumers.py
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone


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

        # Verifica se o usuário tem acesso à sala
        if not await self.is_user_in_room(self.user, self.room_id):
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        print(f"💬 ChatConsumer: Usuário {self.user.username} conectado à sala {self.room_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        print(f"💬 ChatConsumer: Usuário {self.user.username} desconectado da sala {self.room_id}")

    async def receive(self, text_data):
        """Recebe mensagem do WebSocket do cliente"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')
            
            print(f"📩 Mensagem recebida: {message_type} - {data}")

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'file_message':
                await self.handle_file_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'mark_as_read':
                await self.handle_mark_as_read(data)
                
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao decodificar JSON: {e}")
        except Exception as e:
            print(f"❌ Erro no WebSocket receive: {e}")
            import traceback
            traceback.print_exc()

    async def handle_file_message(self, data):
        """Processa mensagem com arquivo/imagem"""
        try:
            file_data = data.get('file_data', {})
            
            if not file_data:
                print("⚠️ file_data vazio")
                return
            
            print(f"📎 Processando arquivo: {file_data.get('name')} de {self.user.username}")
            
            # Salva no banco de dados
            message_obj = await self.save_file_message_to_db(file_data)
            
            if message_obj:
                # Prepara dados para broadcast
                message_data = {
                    'type': 'chat_message',
                    'message_id': str(message_obj.id),
                    'message': '',  # Mensagem vazia para arquivos
                    'message_type': 'file',
                    'file_data': file_data,
                    'username': self.user.get_full_name() or self.user.username,
                    'user_id': self.user.id,
                    'timestamp': message_obj.timestamp.isoformat(),
                    'room_id': str(self.room_id),
                }
                
                print(f"📤 Enviando arquivo para grupo {self.room_group_name}")
                
                # Envia para TODOS no grupo
                await self.channel_layer.group_send(
                    self.room_group_name,
                    message_data
                )
                
                print(f"✅ Mensagem de arquivo enviada!")
            else:
                print("❌ Falha ao salvar arquivo no banco")
                
        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
            import traceback
            traceback.print_exc()

    @database_sync_to_async
    def save_file_message_to_db(self, file_data):
        """Salva mensagem com arquivo no banco de dados"""
        try:
            from .models import ChatRoom, Message
            
            room = ChatRoom.objects.get(id=self.room_id)
            
            # Extrai dados do arquivo
            file_url = file_data.get('url', '')
            file_name = file_data.get('name', 'arquivo')
            file_size = file_data.get('size', 0)
            file_type = file_data.get('type', 'application/octet-stream')
            
            # Determina se é imagem ou arquivo
            is_image = file_type.startswith('image/')
            
            # Cria a mensagem
            message_obj = Message.objects.create(
                room=room,
                user=self.user,
                content='',  # Sem texto
                original_filename=file_name,
                file_size=file_size,
                file_type=file_type,
            )
            
            # Se for imagem, salva no campo image, senão no file_attachment
            # Como o arquivo já foi salvo pelo upload, só guardamos a referência
            if is_image:
                # Remove o prefixo '/midia/' ou '/media/' se existir
                relative_path = file_url
                if relative_path.startswith('/midia/'):
                    relative_path = relative_path[7:]  # Remove '/midia/'
                elif relative_path.startswith('/media/'):
                    relative_path = relative_path[7:]  # Remove '/media/'
                
                message_obj.image = relative_path
            else:
                relative_path = file_url
                if relative_path.startswith('/midia/'):
                    relative_path = relative_path[7:]
                elif relative_path.startswith('/media/'):
                    relative_path = relative_path[7:]
                
                message_obj.file_attachment = relative_path
            
            message_obj.save()
            
            # Atualiza timestamp da sala
            room.updated_at = timezone.now()
            room.save(update_fields=['updated_at'])
            
            print(f"✅ Mensagem de arquivo salva: ID={message_obj.id}, imagem={message_obj.image}, arquivo={message_obj.file_attachment}")
            
            return message_obj
            
        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {e}")
            import traceback
            traceback.print_exc()
            return None


    async def handle_chat_message(self, data):
        """Processa e salva mensagem de chat"""
        try:
            message_text = data.get('message', '').strip()
            
            if not message_text:
                print("⚠️ Mensagem vazia ignorada")
                return
            
            print(f"💬 Processando mensagem: '{message_text}' de {self.user.username}")
            
            # Salva no banco de dados
            message_obj = await self.save_message_to_db(message_text)
            
            if message_obj:
                # Prepara dados para broadcast
                message_data = {
                    'type': 'chat_message',  # Este é o método que será chamado
                    'message_id': str(message_obj.id),
                    'message': message_text,
                    'username': self.user.username,
                    'user_id': self.user.id,
                    'timestamp': message_obj.timestamp.isoformat(),
                    'room_id': str(self.room_id),
                    'is_own': False,  # Será ajustado no cliente
                }
                
                print(f"📤 Enviando para grupo {self.room_group_name}: {message_data}")
                
                # Envia para TODOS no grupo (incluindo o remetente)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    message_data
                )
                
                print(f"✅ Mensagem enviada para o grupo!")
            else:
                print("❌ Falha ao salvar mensagem no banco")
                
        except Exception as e:
            print(f"❌ Erro ao processar mensagem: {e}")
            import traceback
            traceback.print_exc()

    async def chat_message(self, event):
        """Envia mensagem para o WebSocket do cliente"""
        print(f"📨 chat_message chamado para {self.user.username}: {event}")
        
        # Ajusta flag is_own baseado no usuário atual
        event['is_own'] = (event.get('user_id') == self.user.id)
        
        # Envia para o cliente
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            **event
        }))
        
        print(f"✅ Mensagem enviada para cliente {self.user.username}")

    async def handle_typing(self, data):
        """Processa indicador de digitação"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'username': self.user.username,
                'user_id': self.user.id,
                'is_typing': data.get('is_typing', False)
            }
        )

    async def typing_indicator(self, event):
        """Envia indicador de digitação (exceto para o próprio usuário)"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                **event
            }))

    async def handle_mark_as_read(self, data):
        """Marca mensagem como lida"""
        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_as_read(message_id)

# ==================== DATABASE OPERATIONS ====================

    @database_sync_to_async
    def is_user_in_room(self, user, room_id):
        """Verifica se o usuário está na sala"""
        from .models import ChatRoom
        return ChatRoom.objects.filter(id=room_id, participants=user).exists()

    @database_sync_to_async
    def save_message_to_db(self, message_text):
        """Salva mensagem no banco de dados"""
        try:
            from .models import ChatRoom, Message
            
            room = ChatRoom.objects.get(id=self.room_id)
            
            message_obj = Message.objects.create(
                room=room,
                user=self.user,
                content=message_text,
            )
            
            # Atualiza timestamp da sala
            room.updated_at = timezone.now()
            room.save(update_fields=['updated_at'])
            
            print(f"✅ Mensagem salva no banco: ID={message_obj.id}")
            
            return message_obj
            
        except Exception as e:
            print(f"❌ Erro ao salvar mensagem: {e}")
            import traceback
            traceback.print_exc()
            return None

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Marca mensagem como lida"""
        try:
            from .models import Message, MessageRead
            message = Message.objects.get(id=message_id)
            MessageRead.objects.get_or_create(
                message=message,
                user=self.user
            )
        except Exception as e:
            print(f"❌ Erro ao marcar mensagem como lida: {e}")


    