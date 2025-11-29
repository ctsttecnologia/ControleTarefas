
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
    name = models.CharField(max_length=150, blank=True, null=True) # Melhor deixar opcional para DMs
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='DM')
    is_group_chat = models.BooleanField(default=False)
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # NOVO: Adicione isso para saber qual sala teve mensagem recente
    updated_at = models.DateTimeField(auto_now=True) 

    # Relação com o modelo Tarefas
    tarefa = models.ForeignKey(
        'tarefas.Tarefas', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='chat_rooms',
        verbose_name="Tarefa Relacionada"
    )

    def __str__(self):
        return f"{self.name} ({self.room_type})"
    
    def get_room_display_name(self, user):
        """ Retorna o nome de exibição correto da sala. """
        if self.room_type == 'DM':
            other_user = self.participants.exclude(id=user.id).first()
            if other_user:
                return f"{other_user.first_name} {other_user.last_name}".strip() or other_user.username
            return "Usuário Desconhecido"
        return self.name or "Chat Geral"

    def get_last_message_preview(self):
        """ Retorna o conteúdo da última mensagem. """
        last_msg = self.messages.order_by('-timestamp').first()
        if last_msg:
            if last_msg.image:
                return "📷 [Imagem]"
            # Garante que content não seja None antes de fatiar
            content = last_msg.content or ""
            return (content[:40] + '...') if len(content) > 40 else content
        return ""

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # ALTERAÇÃO: null=True, blank=True para permitir envio só de imagem
    content = models.TextField(null=True, blank=True) 
    
    timestamp = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)
    
    # NOVO: Saber se foi lida
    is_read = models.BooleanField(default=False) 

    class Meta:
        db_table = "chat"
        ordering = ['timestamp']
        verbose_name = "Mensagem de Chat"
        verbose_name_plural = "Mensagens de Chat"

    def __str__(self):
        # Proteção caso content seja None
        texto = self.content if self.content else "[Imagem]"
        return f'{self.user.username}: {texto[:50]}'

