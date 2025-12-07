
# chat/models.py

from django.db import models
from django.contrib.auth import get_user_model
import uuid
import os
from django.utils import timezone


User = get_user_model()

class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('DM', 'Direct Message'),
        ('GROUP', 'Group Chat'),
        ('TASK', 'Task Chat'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, blank=True, null=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='DM')
    is_group_chat = models.BooleanField(default=False)
    participants = models.ManyToManyField(
        User, 
        related_name='chat_rooms',
        db_table='chat_rooms_participants',  # Nome explícito da tabela
        through_fields=None  # Deixa o Django gerenciar os campos
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Push notifications settings
    enable_push_notifications = models.BooleanField(default=True)

    # 🔧 RELAÇÃO CONDICIONAL com tarefas
    # Se o app tarefas existir, adiciona a relação
    try:
        from tarefas.models import Tarefas
        tarefa = models.ForeignKey(
            'tarefas.Tarefas', 
            on_delete=models.CASCADE, 
            null=True, 
            blank=True,
            related_name='chat_rooms'
        )
    except (ImportError, ModuleNotFoundError):
        # Se não existir, cria campo genérico
        tarefa_id = models.IntegerField(null=True, blank=True, verbose_name="ID da Tarefa")
        tarefa_titulo = models.CharField(max_length=200, null=True, blank=True, verbose_name="Título da Tarefa")
        tarefa_descricao = models.TextField(null=True, blank=True, verbose_name="Descrição da Tarefa")


    class Meta:
        db_table = "chat_rooms"
        verbose_name = "Sala de Chat"
        verbose_name_plural = "Salas de Chat"

    def __str__(self):
        return f"{self.name} ({self.room_type})"
    
    def get_room_display_name(self, user):
        """Retorna o nome de exibição correto da sala."""
        if self.room_type == 'DM':
            other_user = self.participants.exclude(id=user.id).first()
            if other_user:
                return f"{other_user.first_name} {other_user.last_name}".strip() or other_user.username
            return "Usuário Desconhecido"
        return self.name or "Chat Geral"

    def get_last_message_preview(self):
        """Retorna o conteúdo da última mensagem."""
        last_msg = self.messages.order_by('-timestamp').first()
        if last_msg:
            if last_msg.file_attachment:
                return f"📎 {last_msg.get_file_type_emoji()} Arquivo"
            elif last_msg.image:
                return "📷 [Imagem]"
            content = last_msg.content or ""
            return (content[:40] + '...') if len(content) > 40 else content
        return ""

    def get_unread_count(self, user):
        """Retorna quantidade de mensagens não lidas para o usuário."""
        return self.messages.exclude(
            message_reads__user=user
        ).count()


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    content = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Arquivos e imagens
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)
    file_attachment = models.FileField(upload_to='chat_files/', null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    file_type = models.CharField(max_length=100, null=True, blank=True)
    
    # Mensagem editada
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # Mensagem respondendo a outra
    reply_to = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='replies'
    )

    class Meta:
        db_table = "chat"
        ordering = ['timestamp']
        verbose_name = "Mensagem de Chat"
        verbose_name_plural = "Mensagens de Chat"
        indexes = [
            models.Index(fields=['room', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        if self.file_attachment:
            return f'{self.user.username}: [Arquivo: {self.original_filename}]'
        elif self.image:
            return f'{self.user.username}: [Imagem]'
        else:
            texto = self.content if self.content else "[Mensagem vazia]"
            return f'{self.user.username}: {texto[:50]}'

    def get_file_type_emoji(self):
        """Retorna emoji baseado no tipo do arquivo."""
        if not self.file_type:
            return "📄"
        
        file_type_lower = self.file_type.lower()
        
        if 'image' in file_type_lower:
            return "🖼️"
        elif 'video' in file_type_lower:
            return "🎥"
        elif 'audio' in file_type_lower:
            return "🎵"
        elif 'pdf' in file_type_lower:
            return "📕"
        elif any(word in file_type_lower for word in ['document', 'word', 'doc']):
            return "📘"
        elif any(word in file_type_lower for word in ['spreadsheet', 'excel', 'xls']):
            return "📊"
        elif 'zip' in file_type_lower or 'rar' in file_type_lower:
            return "📦"
        elif 'text' in file_type_lower:
            return "📝"
        else:
            return "📄"

    def get_file_size_display(self):
        """Retorna tamanho do arquivo formatado."""
        if not self.file_size:
            return ""
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class MessageRead(models.Model):
    """Modelo para controlar mensagens lidas."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='message_reads')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user']
        indexes = [
            models.Index(fields=['message', 'user']),
        ]
        verbose_name = "Leitura de Mensagem"
        verbose_name_plural = "Leituras de Mensagens"

    def __str__(self):
        return f'{self.user.username} leu mensagem {self.message.id}'


class PushNotificationSubscription(models.Model):
    """Modelo para armazenar subscrições de push notifications."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    endpoint = models.TextField()
    p256dh_key = models.TextField()
    auth_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'endpoint']
        verbose_name = "Subscrição Push"
        verbose_name_plural = "Subscrições Push"

    def __str__(self):
        return f'Push subscription for {self.user.username}'


class ChatSearchIndex(models.Model):
    """Modelo para indexação de busca otimizada."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='search_index')
    search_text = models.TextField()  # Texto indexável (conteúdo + nome do arquivo)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['room', 'search_text']),
        ]
        verbose_name = "Índice de Busca"
        verbose_name_plural = "Índices de Busca"

    def __str__(self):
        return f'Search index for message {self.message.id}'



