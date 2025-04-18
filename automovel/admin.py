
# automovel/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Carro, Agendamento

@admin.register(Carro)
class CarroAdmin(admin.ModelAdmin):
    list_display = ('placa', 'modelo', 'marca', 'ano', 'status', 'data_proxima_manutencao', 'idade', 'ativo')
    search_fields = ('placa', 'modelo', 'marca', 'renavan')
    list_filter = ('marca', 'ano', 'ativo', 'cor')
    list_editable = ('ativo',)
    list_select_related = True
    ordering = ('marca', 'modelo')
    date_hierarchy = 'data_proxima_manutencao'
    actions = ['marcar_como_inativo', 'agendar_manutencao']
    readonly_fields = ('status', 'idade')
    fieldsets = (
        (_('Informações Básicas'), {
            'fields': ('placa', 'renavan', 'marca', 'modelo', 'cor', 'ano', 'ativo')
        }),
        (_('Manutenção'), {
            'fields': ('data_ultima_manutencao', 'data_proxima_manutencao', 'status')
        }),
        (_('Outras Informações'), {
            'fields': ('observacoes',),
            'classes': ('collapse',)
        }),
    )

    def status(self, obj):
        return obj.status
    status.short_description = _('Status')

    def idade(self, obj):
        return f"{obj.idade} anos"
    idade.short_description = _('Idade')

    def marcar_como_inativo(self, request, queryset):
        updated = queryset.update(ativo=False)
        self.message_user(request, _('{} veículos marcados como inativos.').format(updated))
    marcar_como_inativo.short_description = _('Marcar veículos selecionados como inativos')

    def agendar_manutencao(self, request, queryset):
        for carro in queryset:
            carro.calcular_proxima_manutencao()
        self.message_user(request, _('Manutenção agendada para os veículos selecionados.'))
    agendar_manutencao.short_description = _('Agendar próxima manutenção (90 dias)')

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = (
        'carro', 'funcionario', 'data_hora_formatada', 'status', 
        'duracao_formatada', 'km_percorrido', 'necessita_abastecimento', 'foto_tag_admin'
    )
    list_filter = ('status', 'cancelar_agenda', 'carro__marca', 'pedagio', 'abastecimento')
    search_fields = (
        'funcionario', 'responsavel', 'carro__placa', 
        'carro__modelo', 'carro__marca', 'cm'
    )
    date_hierarchy = 'data_hora_agenda'
    list_select_related = ('carro',)
    raw_id_fields = ('carro',)
    readonly_fields = ('foto_tag_admin', 'status', 'duracao_formatada', 'km_percorrido')
    actions = ['finalizar_agendamentos', 'cancelar_agendamentos']
    
    fieldsets = (
        (_('Informações Básicas'), {
            'fields': ('carro', 'funcionario', 'cm', 'status')
        }),
        (_('Datas e Horários'), {
            'fields': ('data_hora_agenda', 'data_hora_devolucao', 'duracao_formatada')
        }),
        (_('Quilometragem'), {
            'fields': ('km_inicial', 'km_final', 'km_percorrido')
        }),
        (_('Recursos'), {
            'fields': ('pedagio', 'abastecimento', 'necessita_abastecimento')
        }),
        (_('Documentação'), {
            'fields': ('fotos', 'foto_tag_admin', 'assinatura', 'ocorrencia', 'descricao')
        }),
        (_('Controle'), {
            'fields': ('cancelar_agenda', 'motivo_cancelamento', 'responsavel'),
            'classes': ('collapse',)
        }),
    )

    def foto_tag_admin(self, obj):
        if obj.fotos:
            return format_html('<img src="{}" width="150" />', obj.fotos.url)
        return "Nenhuma foto"
    foto_tag_admin.short_description = 'Pré-visualização'
    foto_tag_admin.allow_tags = True

    def data_hora_formatada(self, obj):
        return obj.data_hora_agenda.strftime('%d/%m/%Y %H:%M')
    data_hora_formatada.short_description = _('Data/Hora')
    data_hora_formatada.admin_order_field = 'data_hora_agenda'

    def duracao_formatada(self, obj):
        duracao = obj.duracao_agendamento()
        if duracao:
            hours, remainder = divmod(duracao.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m"
        return "-"
    duracao_formatada.short_description = _('Duração')

    def km_percorrido(self, obj):
        return obj.calcular_quilometragem_percorrida() or "-"
    km_percorrido.short_description = _('Km Percorrido')

    def necessita_abastecimento(self, obj):
        return obj.abastecimento
    necessita_abastecimento.short_description = _('Abastecer?')
    necessita_abastecimento.boolean = True

    def finalizar_agendamentos(self, request, queryset):
        for agendamento in queryset.filter(status='em_andamento'):
            agendamento.finalizar_agendamento(
                km_final=agendamento.km_inicial + 100,
                ocorrencia=_('Finalizado pelo admin')
            )
        self.message_user(request, _('Agendamentos finalizados com sucesso.'))
    finalizar_agendamentos.short_description = _('Finalizar agendamentos selecionados')

    def cancelar_agendamentos(self, request, queryset):
        updated = queryset.update(
            cancelar_agenda=True,
            status='cancelado',
            motivo_cancelamento=_('Cancelado pelo administrador')
        )
        self.message_user(request, _('{} agendamentos cancelados.').format(updated))
    cancelar_agendamentos.short_description = _('Cancelar agendamentos selecionados')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('carro')
        