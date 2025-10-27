# chat/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings # Para acessar MEDIA_ROOT/URL
import uuid # Para IDs únicos de sala
from tarefas.models import Tarefas

User = get_user_model()


class ChatRoom(models.Model):
    # Usaremos UUID para IDs de sala mais seguros e difíceis de adivinhar
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Nome para salas de grupo (pode ser None para DMs ou chats de tarefa, onde o nome é inferido)
    name = models.CharField(max_length=255, blank=True, null=True, unique=False)
    
    # Tipo da sala (Grupo, Individual, Tarefa)
    ROOM_TYPE_CHOICES = [
        ('group', 'Grupo'),
        ('individual', 'Individual'),
        ('task', 'Tarefa'),
    ]
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE_CHOICES, default='group')

    # Para salas individuais: os dois usuários envolvidos
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='individual_chats_as_user1', null=True, blank=True)
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='individual_chats_as_user2', null=True, blank=True)

    # Para salas de grupo e tarefa: lista de membros
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_rooms', blank=True)
    
    # Para salas de tarefa: link para a tarefa
    task = models.OneToOneField(Tarefas, on_delete=models.CASCADE, related_name='chat_room', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Garante que não haja duas DMs entre os mesmos dois usuários
        unique_together = ('user1', 'user2', 'room_type') 

    def __str__(self):
        if self.room_type == 'individual':
            if self.user1 and self.user2:
                return f"DM: {self.user1.username} e {self.user2.username}"
            return "DM (Usuários não definidos)"
        elif self.room_type == 'task' and self.task:
            return f"Chat da Tarefa: {self.task.titulo}"
        return self.name or f"Sala de Grupo #{self.id}"

    # Método auxiliar para verificar se um usuário é participante
    def is_participant(self, user):
        if self.room_type == 'individual':
            return user == self.user1 or user == self.user2
        elif self.room_type == 'task':
            # Responsável e Participantes da Tarefa + convidados adicionais à sala de chat
            return user == self.task.responsavel or user in self.task.participantes.all() or user in self.participants.all()
        return user in self.participants.all() # Para salas de grupo


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True) # Mensagem de texto (pode ser vazia se for só imagem)
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True) # Para imagens
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('timestamp',)

    def __str__(self):
        if self.image:
            return f'{self.user.username}: [Imagem]'
        return f'{self.user.username}: {self.content[:50]}'

    def get_image_url(self):
        if self.image:
            return self.image.url
        return None