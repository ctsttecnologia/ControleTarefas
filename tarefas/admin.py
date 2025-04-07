from django.contrib import admin
from .models import Tarefas
from django.utils.html import format_html

admin.site.register(Tarefas)

# Primeiro tente desregistrar se já estiver registrado
try:
    admin.site.unregister(Tarefas)
except admin.sites.NotRegistered:
    pass


# Agora registre com sua classe customizada
@admin.register(Tarefas)
class TarefasAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'nome', 'get_status_display', 'data_criacao', 'prazo')
    list_filter = ('status', 'data_criacao')
    search_fields = ('titulo', 'nome', 'descricao')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    
    fieldsets = (
        (None, {
            'fields': ('titulo', 'nome', 'descricao')
        }),
        ('Status e Datas', {
            'fields': ('status', 'prazo', 'data_criacao', 'data_atualizacao')
        }),
    )