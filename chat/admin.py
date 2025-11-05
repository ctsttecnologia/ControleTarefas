
# chat/admin.py
from django.contrib import admin
from .models import ChatRoom, Message

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_type', 'is_group_chat', 'created_at']
    list_filter = ['room_type', 'is_group_chat', 'created_at']
    filter_horizontal = ['participants']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'room_type', 'is_group_chat', 'tarefa')
        }),
        ('Participantes', {
            'fields': ('participants',)
        }),
        ('Metadados', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['room', 'user', 'content_preview', 'timestamp']
    list_filter = ['timestamp', 'room__room_type']
    search_fields = ['content', 'user__username', 'room__name']
    readonly_fields = ['timestamp']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Conteúdo'

