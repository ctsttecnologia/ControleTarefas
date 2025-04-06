from django.contrib import admin
from .models import Carro, Agendamento

@admin.register(Carro)
class CarroAdmin(admin.ModelAdmin):
    list_display = ('placa', 'modelo', 'marca', 'cor', 'ano', 'renavan')
    search_fields = ('placa', 'modelo', 'marca', 'renavan')
    list_filter = ('marca', 'ano')

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('carro', 'funcionario', 'data_hora_agenda', 'data_hora_devolucao', 'cancelar_agenda')
    list_filter = ('cancelar_agenda', 'carro')
    search_fields = ('funcionario', 'carro__nome', 'carro__modelo')
    date_hierarchy = 'data_hora_agenda'