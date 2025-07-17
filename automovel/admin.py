# automovel/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Carro, Agendamento, Checklist, Foto

@admin.register(Carro)
class CarroAdmin(admin.ModelAdmin):
    """
    Admin para o modelo Carro.
    - list_editable: Permite editar o status 'disponivel' diretamente na lista.
    """
    list_display = ('placa', 'modelo', 'marca', 'ano', 'disponivel', 'ativo')
    list_filter = ('marca', 'disponivel', 'ativo')
    search_fields = ('placa', 'modelo', 'marca')
    list_editable = ('disponivel', 'ativo')
    list_per_page = 20

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    """
    Admin para o modelo Agendamento.
    - autocomplete_fields: Facilita a busca de carros e usuários.
    - date_hierarchy: Permite navegar pelos agendamentos por data.
    """
    list_display = ('id', 'carro', 'funcionario', 'data_hora_agenda', 'status', 'usuario')
    list_filter = ('status', 'carro', 'data_hora_agenda')
    search_fields = ('funcionario', 'carro__placa', 'usuario__username')
    autocomplete_fields = ('carro', 'usuario')
    date_hierarchy = 'data_hora_agenda'
    list_per_page = 20

@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    """
    Admin para o modelo Checklist.
    - Corrigido 'data_criacao' para 'data_hora'.
    """
    list_display = ('id', 'agendamento', 'tipo', 'data_hora', 'usuario') # CORRIGIDO AQUI
    list_filter = ('tipo', 'data_hora')
    search_fields = ('agendamento__carro__placa', 'agendamento__funcionario')
    autocomplete_fields = ('agendamento', 'usuario')
    date_hierarchy = 'data_hora'
    list_per_page = 20

@admin.register(Foto)
class FotoAdmin(admin.ModelAdmin):
    """
    Admin para o modelo Foto.
    - Adicionado preview da imagem na lista.
    """
    list_display = ('id', 'agendamento', 'data_criacao', 'image_preview')
    list_filter = ('data_criacao',)
    search_fields = ('agendamento__id',)
    autocomplete_fields = ('agendamento',)

    def image_preview(self, obj):
        if obj.imagem:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" width="80" /></a>', obj.imagem.url)
        return "Sem imagem"
    image_preview.short_description = 'Preview da Imagem'