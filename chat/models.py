
# chat/models.py

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from core.upload import delete_old_file, safe_delete_file
from core.validators import SecureFileValidator

User = get_user_model()


# ══════════════════════════════════════════════
# UPLOAD PATHS
# ══════════════════════════════════════════════

def chat_image_path(instance, filename):
    """
    Organiza imagens por sala: media/chat/<room_id>/images/<filename>
    """
    return f'chat/{instance.room_id}/images/{filename}'


def chat_file_path(instance, filename):
    """
    Organiza arquivos por sala: media/chat/<room_id>/files/<filename>
    """
    return f'chat/{instance.room_id}/files/{filename}'


# ══════════════════════════════════════════════
# CHAT ROOM
# ══════════════════════════════════════════════

class ChatRoom(models.Model):

    ROOM_TYPES = [
        ('DM',    'Direct Message'),
        ('GROUP', 'Group Chat'),
        ('TASK',  'Task Chat'),
    ]

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name      = models.CharField(max_length=150, blank=True, null=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='DM')

    is_group_chat = models.BooleanField(default=False)

    participants = models.ManyToManyField(
        User,
        related_name='chat_rooms',
        db_table='chat_rooms_participants',
    )

    # ── Relação com Tarefa ─────────────────────────────────────────────────
    # Usa string lazy → sem try/except, sem risco nas migrations.
    # null=True garante que salas sem tarefa funcionem normalmente.
    tarefa = models.ForeignKey(
        'tarefas.Tarefas',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_rooms',
        verbose_name=_("Tarefa Relacionada"),
    )
    # ──────────────────────────────────────────────────────────────────────

    enable_push_notifications = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = "chat_rooms"
        verbose_name    = "Sala de Chat"
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
        if not last_msg:
            return ""
        if last_msg.file_attachment:
            return f"📎 {last_msg.get_file_type_emoji()} Arquivo"
        if last_msg.image:
            return "📷 [Imagem]"
        content = last_msg.content or ""
        return (content[:40] + '…') if len(content) > 40 else content

    def get_unread_count(self, user):
        """Retorna quantidade de mensagens não lidas para o usuário."""
        return self.messages.exclude(message_reads__user=user).count()


# ══════════════════════════════════════════════
# MESSAGE
# ══════════════════════════════════════════════

class Message(models.Model):

    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    content = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # ── Uploads ───────────────────────────────────────────────────────────
    image = models.ImageField(
        upload_to=chat_image_path,
        null=True,
        blank=True,
        validators=[SecureFileValidator('chat_imagens')],
        verbose_name=_("Imagem"),
    )
    file_attachment = models.FileField(
        upload_to=chat_file_path,
        null=True,
        blank=True,
        validators=[SecureFileValidator('chat_arquivos')],
        verbose_name=_("Arquivo Anexado"),
    )
    # ─────────────────────────────────────────────────────────────────────

    original_filename = models.CharField(max_length=255, null=True, blank=True)
    file_size         = models.BigIntegerField(null=True, blank=True)
    file_type         = models.CharField(max_length=100, null=True, blank=True)

    # ── Edição ────────────────────────────────────────────────────────────
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    # ── Resposta ──────────────────────────────────────────────────────────
    reply_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replies',
    )

    class Meta:
        db_table = "chat"
        ordering = ['timestamp']
        verbose_name        = "Mensagem de Chat"
        verbose_name_plural = "Mensagens de Chat"
        indexes = [
            models.Index(fields=['room', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        if self.file_attachment:
            return f'{self.user.username}: [Arquivo: {self.original_filename}]'
        if self.image:
            return f'{self.user.username}: [Imagem]'
        texto = self.content or "[Mensagem vazia]"
        return f'{self.user.username}: {texto[:50]}'

    # ── Gerenciamento de arquivos ─────────────────────────────────────────

    def save(self, *args, **kwargs):
        delete_old_file(self, 'image')
        delete_old_file(self, 'file_attachment')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        safe_delete_file(self, 'image')
        safe_delete_file(self, 'file_attachment')
        super().delete(*args, **kwargs)

    # ── Helpers ───────────────────────────────────────────────────────────

    def get_file_type_emoji(self):
        """Retorna emoji baseado no tipo do arquivo."""
        if not self.file_type:
            return "📄"
        ft = self.file_type.lower()
        if 'image'                                              in ft: return "🖼️"
        if 'video'                                              in ft: return "🎥"
        if 'audio'                                              in ft: return "🎵"
        if 'pdf'                                                in ft: return "📕"
        if any(w in ft for w in ['document', 'word', 'doc'])        : return "📘"
        if any(w in ft for w in ['spreadsheet', 'excel', 'xls'])    : return "📊"
        if any(w in ft for w in ['zip', 'rar'])                     : return "📦"
        if 'text'                                               in ft: return "📝"
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


# ══════════════════════════════════════════════
# MESSAGE READ
# ══════════════════════════════════════════════

class MessageRead(models.Model):
    """Controla quais mensagens cada usuário já leu."""

    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='message_reads')
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user']
        indexes = [
            models.Index(fields=['message', 'user']),
        ]
        verbose_name        = "Leitura de Mensagem"
        verbose_name_plural = "Leituras de Mensagens"

    def __str__(self):
        return f'{self.user.username} leu mensagem {self.message.id}'


# ══════════════════════════════════════════════
# PUSH NOTIFICATION SUBSCRIPTION
# ══════════════════════════════════════════════

class PushNotificationSubscription(models.Model):
    """Armazena subscrições de push notifications por usuário/dispositivo."""

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.ForeignKey(User, on_delete=models.CASCADE)
    endpoint  = models.CharField(max_length=512)
    p256dh_key = models.CharField(max_length=128)
    auth_key  = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'endpoint']
        verbose_name        = "Subscrição Push"
        verbose_name_plural = "Subscrições Push"

    def __str__(self):
        return f'Push subscription for {self.user.username}'


# ══════════════════════════════════════════════
# CHAT SEARCH INDEX
# ══════════════════════════════════════════════

class ChatSearchIndex(models.Model):
    """Indexação de busca otimizada sobre mensagens."""

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message     = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='search_index')
    search_text = models.TextField()
    room        = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['room']),
        ]
        verbose_name        = "Índice de Busca"
        verbose_name_plural = "Índices de Busca"

    def __str__(self):
        return f'Search index for message {self.message.id}'

