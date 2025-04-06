from django.contrib import admin
from .models import TipoTreinamento, Treinamento

class TipoTreinamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'modalidade', 'descricao')
    search_fields = ('nome',)
    list_filter = ('modalidade',)

class TreinamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_treinamento', 'data_inicio', 'data_vencimento', 'funcionario')
    search_fields = ('nome', 'funcionario', 'cm')
    list_filter = ('tipo_treinamento', 'data_inicio')
    date_hierarchy = 'data_inicio'
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('tipo_treinamento', 'nome', 'descricao')
        }),
        ('Datas e Duração', {
            'fields': ('data_inicio', 'data_vencimento', 'duracao', 'hxh')
        }),
        ('Responsáveis', {
            'fields': ('funcionario', 'cm', 'palestrante')
        }),
        ('Detalhes', {
            'fields': ('atividade',)
        }),
    )

admin.site.register(TipoTreinamento, TipoTreinamentoAdmin)
admin.site.register(Treinamento, TreinamentoAdmin)

