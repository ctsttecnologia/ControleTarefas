
# notifications/admin.py

from django.contrib import admin
from .models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = [
        'titulo', 'usuario', 'tipo', 'categoria',
        'prioridade', 'lida', 'data_criacao',
    ]
    list_filter = ['tipo', 'categoria', 'prioridade', 'lida', 'data_criacao']
    search_fields = ['titulo', 'mensagem', 'usuario__username']
    list_editable = ['lida']
    readonly_fields = ['data_criacao', 'data_leitura']
    date_hierarchy = 'data_criacao'

    actions = ['marcar_como_lida', 'marcar_como_nao_lida']

    @admin.action(description='Marcar como lida')
    def marcar_como_lida(self, request, queryset):
        from django.utils import timezone
        queryset.update(lida=True, data_leitura=timezone.now())

    @admin.action(description='Marcar como não lida')
    def marcar_como_nao_lida(self, request, queryset):
        queryset.update(lida=False, data_leitura=None)

