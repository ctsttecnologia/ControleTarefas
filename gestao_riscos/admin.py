from django.contrib import admin
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin
from .models import Incidente, Inspecao, CartaoTag



@admin.register(Incidente)
class IncidenteAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
  
    list_display = ('descricao', 'setor', 'tipo_incidente', 'data_ocorrencia', 'registrado_por', 'filial')
    list_filter = ('setor', 'tipo_incidente', 'data_ocorrencia', 'filial')
    search_fields = ('descricao', 'detalhes', 'setor')
    date_hierarchy = 'data_ocorrencia'
    readonly_fields = ('filial',) # Impede a edição da filial após a criação.

@admin.register(Inspecao)
class InspecaoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
  
    list_display = ('__str__', 'data_agendada', 'status', 'responsavel', 'filial')
    list_filter = ('status', 'data_agendada', 'filial')
    search_fields = ('equipamento__nome', 'responsavel__username')
    autocomplete_fields = ['equipamento', 'responsavel']
    readonly_fields = ('filial',) # Impede a edição da filial após a criação.

@admin.register(CartaoTag)
class CartaoTagAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    """Admin para Cartões de Bloqueio (Tags)."""
    list_display = ('funcionario', 'cargo', 'fone', 'data_criacao', 'data_validade', 'ativo', 'filial')
    list_filter = ('ativo', 'data_validade', 'filial')
    search_fields = ('funcionario__nome_completo',)
    autocomplete_fields = ['funcionario']
    readonly_fields = ('filial',) # Impede a edição da filial após a criação.
