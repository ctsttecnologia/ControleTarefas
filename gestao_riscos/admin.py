from django.contrib import admin
from core.mixins import FilialAdminScopedMixin, ChangeFilialAdminMixin
from .models import Incidente, Inspecao, CartaoTag


@admin.register(Incidente)
class IncidenteAdmin(FilialAdminScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
  
    list_display = ('descricao', 'setor', 'tipo_incidente', 'data_ocorrencia', 'registrado_por', 'filial')
    list_filter = ('setor', 'tipo_incidente', 'data_ocorrencia', 'filial')
    search_fields = ('descricao', 'detalhes', 'setor')
    date_hierarchy = 'data_ocorrencia'

@admin.register(Inspecao)
class InspecaoAdmin(FilialAdminScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
  
    list_display = ('__str__', 'data_agendada', 'status', 'inspetor', 'filial')
    list_filter = ('status', 'data_agendada', 'filial')
    search_fields = ('equipamento__nome', 'inspetor__username')
    autocomplete_fields = ['equipamento', 'inspetor']

@admin.register(CartaoTag)
class CartaoTagAdmin(FilialAdminScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    """Admin para Cartões de Bloqueio (Tags)."""
    list_display = ('funcionario', 'fone', 'data_criacao', 'data_validade', 'ativo', 'filial')
    list_filter = ('ativo', 'data_validade', 'filial')
    search_fields = ('funcionario__nome_completo',)
    autocomplete_fields = ['funcionario']
