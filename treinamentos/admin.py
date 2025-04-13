from django.contrib import admin
from .models import TipoTreinamento, Treinamento
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

@admin.register(TipoTreinamento)
class TipoTreinamentoAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'modalidade_badge',
        'ativo',
        'area_formatada',
        'validade_meses',
        'certificado_simbolo',
        'status_badge',
        
    )
    
    list_filter = (
        'modalidade',
        'area',
        'ativo',
    )
    
    search_fields = (
        'nome',
        'descricao',
    )
    
    list_editable = (
        'ativo',
        'validade_meses',
    )
    
    readonly_fields = (
        'data_cadastro',
        'data_atualizacao',
    )
    
    fieldsets = (
        (None, {
            'fields': (
                'nome',
                'modalidade',
                'area',
                'descricao'
            )
        }),
        (_('Configurações'), {
            'fields': (
                'certificado',
                'validade_meses',
                'ativo'
            )
        }),
        (_('Auditoria'), {
            'fields': (
                'data_cadastro',
                'data_atualizacao'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'ativar_tipos',
        'desativar_tipos',
    ]

    def modalidade_badge(self, obj):
        colors = {
            'I': 'blue',
            'E': 'green',
            'H': 'purple',
            'O': 'orange'
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            colors.get(obj.modalidade, 'gray'), obj.modalidade_formatada
        )
    modalidade_badge.short_description = _('Modalidade')
    modalidade_badge.admin_order_field = 'modalidade'
    
    def certificado_simbolo(self, obj):
        return '✓' if obj.certificado else '✗'
    certificado_simbolo.short_description = _('Certificado')
    certificado_simbolo.admin_order_field = 'certificado'
    
    def status_badge(self, obj):
        color = 'green' if obj.ativo else 'red'
        text = _('Ativo') if obj.ativo else _('Inativo')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            color, text
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'ativo'
    
    def ativar_tipos(self, request, queryset):
        updated = queryset.update(ativo=True)
        self.message_user(request, _('%d tipos de treinamento ativados') % updated)
    ativar_tipos.short_description = _('Ativar tipos selecionados')
    
    def desativar_tipos(self, request, queryset):
        updated = queryset.update(ativo=False)
        self.message_user(request, _('%d tipos de treinamento desativados') % updated)
    desativar_tipos.short_description = _('Desativar tipos selecionados')

@admin.register(Treinamento)
class TreinamentoAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'tipo_treinamento_link',
        'data_inicio_formatada',
        'status_badge',
        'tempo_restante_dias',
        'custo_total_formatado',
        'participantes_previstos',
        'palestrante'
        
    )
    
    list_filter = (
        'tipo_treinamento',
        'status',
        'data_inicio',
    )
    
    search_fields = (
        'nome',
        'funcionario',
        'cm',
        'palestrante',
        'atividade'
    )
    
    readonly_fields = (
        'data_cadastro',
        'data_atualizacao',
        'custo_total_estimado',
        'carga_horaria_total',
    )
    
    date_hierarchy = 'data_inicio'
    
    fieldsets = (
        (_('Informações Básicas'), {
            'fields': (
                'tipo_treinamento',
                'nome',
                'descricao',
                'atividade',
                'status'
            )
        }),
        (_('Datas e Horas'), {
            'fields': (
                'data_inicio',
                'data_vencimento',
                'duracao',
                'hxh',
            )
        }),
        (_('Recursos'), {
            'fields': (
                'local',
                'custo',
                'participantes_previstos',
                'custo_total_estimado',
                'carga_horaria_total',
            )
        }),
        (_('Responsáveis'), {
            'fields': (
                'funcionario',
                'cm',
                'palestrante',
            )
        }),
        (_('Auditoria'), {
            'fields': (
                'data_cadastro',
                'data_atualizacao',
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'marcar_como_concluidos',
        'cancelar_treinamentos',
        'atualizar_vencimentos',
    ]

    def tipo_treinamento_link(self, obj):
        url = reverse('admin:gestao_tipotreinamento_change', args=[obj.tipo_treinamento.id])
        return format_html('<a href="{}">{}</a>', url, obj.tipo_treinamento)
    tipo_treinamento_link.short_description = _('Tipo de Treinamento')
    tipo_treinamento_link.admin_order_field = 'tipo_treinamento'
    
    def data_inicio_formatada(self, obj):
        return obj.data_inicio.strftime('%d/%m/%Y %H:%M')
    data_inicio_formatada.short_description = _('Data de Início')
    data_inicio_formatada.admin_order_field = 'data_inicio'
    
    def status_badge(self, obj):
        colors = {
            'P': 'gray',
            'A': 'blue',
            'E': 'orange',
            'C': 'green',
            'X': 'red'
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            colors.get(obj.status, 'gray'), obj.status_formatada
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'status'
    
    def tempo_restante_dias(self, obj):
        if obj.tempo_restante > 0:
            return f"{obj.tempo_restante} dias"
        elif obj.data_inicio.date() == timezone.now().date():
            return _("Hoje")
        elif obj.data_inicio < timezone.now():
            return _("Em andamento/concluído")
        return "-"
    tempo_restante_dias.short_description = _('Dias Restantes')
    tempo_restante_dias.admin_order_field = 'data_inicio'
    
    def custo_total_formatado(self, obj):
        return f"R$ {obj.custo_total_estimado:,.2f}"
    custo_total_formatado.short_description = _('Custo Total')
    custo_total_formatado.admin_order_field = 'custo'
    
    def marcar_como_concluidos(self, request, queryset):
        updated = queryset.filter(status__in=['P', 'A', 'E']).update(status='C')
        self.message_user(request, _('%d treinamentos marcados como concluídos') % updated)
    marcar_como_concluidos.short_description = _('Marcar como concluídos')
    
    def cancelar_treinamentos(self, request, queryset):
        updated = queryset.filter(status__in=['P', 'A']).update(status='X')
        self.message_user(request, _('%d treinamentos cancelados') % updated)
    cancelar_treinamentos.short_description = _('Cancelar treinamentos')
    
    def atualizar_vencimentos(self, request, queryset):
        for treinamento in queryset:
            if treinamento.tipo_treinamento:
                treinamento.data_vencimento = treinamento.data_inicio.date() + timedelta(
                    days=30 * treinamento.tipo_treinamento.validade_meses
                )
                treinamento.save()
        self.message_user(request, _('Vencimentos atualizados com base na validade do tipo'))
    atualizar_vencimentos.short_description = _('Atualizar datas de vencimento')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tipo_treinamento')

