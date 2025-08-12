# automovel/admin.py

# automovel/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Carro, Agendamento, Checklist, Foto
from core.mixins import FilialScopedQuerysetMixin

# CORREÇÃO: O uso do FilialAdminMixin agora é CRÍTICO.
# Ele deve garantir que:
# 1. O método `get_queryset` filtre os objetos pela filial do usuário.
# 2. O método `save_model` atribua a filial do usuário ao criar um novo objeto.
# Sem isso, a criação de objetos no admin irá falhar, pois o campo `filial` é obrigatório.

@admin.register(Carro)
class CarroAdmin(FilialScopedQuerysetMixin, admin.ModelAdmin):
    list_display = ('placa', 'modelo', 'marca', 'filial', 'disponivel', 'ativo')
    list_filter = ('filial', 'marca', 'disponivel', 'ativo')
    search_fields = ('placa', 'modelo', 'marca')
    list_editable = ('disponivel', 'ativo')
    list_per_page = 20

@admin.register(Agendamento)
class AgendamentoAdmin(FilialScopedQuerysetMixin, admin.ModelAdmin):
    list_display = ('id', 'carro', 'funcionario', 'data_hora_agenda', 'status', 'filial')
    list_filter = ('filial', 'status', 'carro', 'data_hora_agenda')
    search_fields = ('funcionario', 'carro__placa', 'usuario__username')
    autocomplete_fields = ('carro', 'usuario')
    date_hierarchy = 'data_hora_agenda'
    list_per_page = 20

@admin.register(Checklist)
class ChecklistAdmin(FilialScopedQuerysetMixin, admin.ModelAdmin):
    list_display = ('id', 'agendamento', 'tipo', 'data_hora', 'filial')
    list_filter = ('filial', 'tipo', 'data_hora')
    search_fields = ('agendamento__carro__placa', 'agendamento__funcionario')
    autocomplete_fields = ('agendamento', 'usuario')
    date_hierarchy = 'data_hora'
    list_per_page = 20

@admin.register(Foto)
class FotoAdmin(FilialScopedQuerysetMixin, admin.ModelAdmin):
    list_display = ('id', 'agendamento', 'data_criacao', 'image_preview', 'filial')
    list_filter = ('filial', 'data_criacao',)
    search_fields = ('agendamento__id',)
    autocomplete_fields = ('agendamento',)

    def image_preview(self, obj):
        if obj.imagem:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" width="80" /></a>', obj.imagem.url)
        return "Sem imagem"
    image_preview.short_description = 'Preview da Imagem'


