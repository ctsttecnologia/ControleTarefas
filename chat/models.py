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

