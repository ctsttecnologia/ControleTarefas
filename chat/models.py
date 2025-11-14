# chat/models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('DM', 'Direct Message'),
        ('GROUP', 'Group Chat'),
        ('TASK', 'Task Chat'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='DM')
    is_group_chat = models.BooleanField(default=False)
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)

    # Relação com o modelo Tarefas existente
    tarefa = models.ForeignKey(
        'tarefas.Tarefas',  # Nome correto do seu modelo
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='chat_rooms',
        verbose_name="Tarefa Relacionada"
    )

    def __str__(self):
        return f"{self.name} ({self.room_type})"
    
    def get_room_display_name(self, user):
        """ Retorna o nome de exibição correto da sala para um usuário específico. """
        if self.room_type == 'DM':
            # Para DMs, retorna o nome do OUTRO participante
            other_user = self.participants.exclude(id=user.id).first()
            if other_user:
                return other_user.get_full_name() or other_user.username
            return "Chat Excluído"
        
        # Para Grupos ou Tarefas, retorna o nome da sala
        return self.name

    def get_last_message_preview(self):
        """ Retorna o conteúdo da última mensagem para a pré-visualização. """
        last_msg = self.messages.order_by('-timestamp').first()
        if last_msg:
            if last_msg.image:
                return "[Imagem]"
            # Limita a pré-visualização para 40 caracteres
            return (last_msg.content[:40] + '...') if len(last_msg.content) > 40 else last_msg.content
        return "Nenhuma mensagem"

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)

    class Meta:
        db_table = "chat"
        ordering = ['timestamp']
        verbose_name = "Mensagem de Chat"
        verbose_name_plural = "Mensagens de Chat"

    def __str__(self):
        return f'{self.user.username}: {self.content[:100]}'

