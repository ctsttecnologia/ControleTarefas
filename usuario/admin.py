from django.contrib import admin
from .models import TipoTreinamento, Treinamento

@admin.register(TipoTreinamento)
class TipoTreinamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'modalidade', 'descricao_curta')
    list_filter = ('modalidade',)
    search_fields = ('nome', 'descricao')
    list_per_page = 20
    
    def descricao_curta(self, obj):
        return obj.descricao[:50] + '...' if obj.descricao else '-'
    descricao_curta.short_description = 'Descrição (resumo)'

@admin.register(Treinamento)
class TreinamentoAdmin(admin.ModelAdmin):
    list_display = (
        'nome', 
        'tipo_treinamento', 
        'data_inicio_formatada', 
        'data_vencimento_formatada',
        'duracao',
        'funcionario'
    )
    list_filter = ('tipo_treinamento', 'data_inicio')
    search_fields = ('nome', 'funcionario', 'cm', 'palestrante')
    raw_id_fields = ('tipo_treinamento',)
    date_hierarchy = 'data_inicio'
    list_per_page = 30
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
        ('Detalhes Adicionais', {
            'fields': ('atividade',)
        }),
    )

    def data_inicio_formatada(self, obj):
        return obj.data_inicio.strftime('%d/%m/%Y')
    data_inicio_formatada.short_description = 'Data Início'
    data_inicio_formatada.admin_order_field = 'data_inicio'

    def data_vencimento_formatada(self, obj):
        return obj.data_vencimento.strftime('%d/%m/%Y')
    data_vencimento_formatada.short_description = 'Data Vencimento'
    data_vencimento_formatada.admin_order_field = 'data_vencimento'

    actions = ['marcar_como_concluido']

    def marcar_como_concluido(self, request, queryset):
        queryset.update(status='C')
    marcar_como_concluido.short_description = "Marcar como concluído"

    def dias_restantes(self, obj):
        return (obj.data_vencimento - date.today()).days
    dias_restantes.short_description = 'Dias Restantes'