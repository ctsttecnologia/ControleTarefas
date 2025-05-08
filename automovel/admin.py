from django.contrib import admin
from .models import Carro, Agendamento, Checklist, Foto

@admin.register(Carro)
class CarroAdmin(admin.ModelAdmin):
    list_display = ('placa', 'modelo', 'marca', 'ano', 'disponivel')
    list_filter = ('marca', 'disponivel', 'ativo')
    search_fields = ('placa', 'modelo', 'marca')

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'carro', 'data_hora_agenda', 'status')
    list_filter = ('status', 'carro')
    search_fields = ('funcionario', 'carro__placa')

@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = ('agendamento', 'tipo', 'data_criacao')
    list_filter = ('tipo',)

@admin.register(Foto)
class FotoAdmin(admin.ModelAdmin):
    list_display = ('agendamento', 'data_criacao')
