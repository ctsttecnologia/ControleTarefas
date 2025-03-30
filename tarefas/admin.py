from django.contrib import admin
from django.utils.html import format_html
from .models import (Tarefas)


@admin.register(Tarefas)
class TarefasAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'nome', 'status', 'data_inicio', 'prazo')
    list_filter = ('status', 'projeto', 'data_inicio')
    search_fields = ('titulo', 'nome', 'responsavel')
    date_hierarchy = 'data_inicio'
    list_editable = ('status',)
    readonly_fields = ('data_cadastro',)
