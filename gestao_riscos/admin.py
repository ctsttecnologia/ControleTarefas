# gestao_riscos/admin.py

from django.contrib import admin
from .models import Incidente, Inspecao

@admin.register(Incidente)
class IncidenteAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'setor', 'tipo_incidente', 'data_ocorrencia', 'registrado_por')
    list_filter = ('setor', 'tipo_incidente', 'data_ocorrencia')
    search_fields = ('descricao', 'detalhes', 'setor')
    date_hierarchy = 'data_ocorrencia'

@admin.register(Inspecao)
class InspecaoAdmin(admin.ModelAdmin):
    list_display = ('equipamento', 'data_agendada', 'status', 'inspetor')
    list_filter = ('status', 'data_agendada')
    search_fields = ('equipamento_nome_equipamento', 'inspetor__username')
    autocomplete_fields = ['equipamento', 'inspetor']