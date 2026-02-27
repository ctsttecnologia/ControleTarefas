
# aparelhos/admin.py
from django.contrib import admin
from .models import Marca, Modelo, Aparelho, Operadora, Plano, LinhaTelefonica, Vinculo
from .models import RecargaCredito
from django.utils.html import format_html
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin




@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'criado_em')
    search_fields = ('nome',)

@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    list_display = ('nome', 'marca', 'criado_em')
    list_filter = ('marca',)
    search_fields = ('nome', 'marca__nome')

@admin.register(Aparelho)
class AparelhoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('__str__', 'filial', 'status', 'data_aquisicao')
    list_filter = ('status', 'filial', 'modelo__marca')
    search_fields = ('numero_serie', 'modelo__nome')
    readonly_fields = ('filial',) # A filial é definida na criação e não deve ser alterada
    list_select_related = ('modelo', 'modelo__marca', 'filial')

@admin.register(Operadora)
class OperadoraAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'operadora', 'valor_mensal', 'franquia_dados_gb')
    list_filter = ('operadora',)
    search_fields = ('nome', 'operadora__nome')

@admin.register(LinhaTelefonica)
class LinhaTelefonicaAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('numero', 'filial', 'plano', 'status', 'data_ativacao')
    list_filter = ('status', 'filial', 'plano__operadora')
    search_fields = ('numero',)
    readonly_fields = ('filial',)
    list_select_related = ('plano', 'plano__operadora', 'filial')


@admin.register(Vinculo)
class VinculoAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'aparelho', 'linha', 'data_entrega', 'data_devolucao', 'status')
    list_filter = ('status', 'funcionario__filial')
    search_fields = (
        'funcionario__nome_completo', 
        'aparelho__modelo__nome', 
        'aparelho__numero_serie', 
        'linha__numero'
    )
    autocomplete_fields = ['funcionario', 'aparelho', 'linha']
    list_select_related = ('funcionario', 'aparelho__modelo', 'linha')
    
    def get_queryset(self, request):
        # Filtra os vínculos pela filial ativa do usuário
        qs = super().get_queryset(request)
        filial_id = request.session.get('active_filial_id')
        if filial_id and not request.user.is_superuser:
            qs = qs.filter(funcionario__filial_id=filial_id)
        return qs
    
@admin.register(RecargaCredito)
class RecargaCreditoAdmin(admin.ModelAdmin):
    list_display = [
        'linha',
        'tipo_recarga',
        'valor_formatado',
        'usuario_credito',
        'responsavel',
        'data_recarga',
        'status_badge',
        'filial',
    ]
    list_filter = [
        'status',
        'tipo_recarga',
        'filial',
        'data_recarga',
        'linha__plano__operadora',
    ]
    search_fields = [
        'linha__numero',
        'usuario_credito__nome_completo',
        'responsavel__nome_completo',
        'codigo_transacao',
    ]
    readonly_fields = [
        'data_solicitacao',
        'atualizado_em',
        'criado_por',
        'historico',
        'dias_vigencia',
        'is_vigente',
    ]
    autocomplete_fields = ['linha', 'responsavel', 'usuario_credito']
    date_hierarchy = 'data_recarga'
    ordering = ['-data_solicitacao']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('filial', 'linha', 'status')
        }),
        ('Responsáveis', {
            'fields': ('responsavel', 'usuario_credito')
        }),
        ('Valores e Tipo', {
            'fields': ('tipo_recarga', 'valor', 'franquia_dados_mb', 'minutos_voz')
        }),
        ('Datas', {
            'fields': ('data_recarga', 'data_inicio', 'data_termino', 'dias_vigencia', 'is_vigente')
        }),
        ('Comprovação', {
            'fields': ('codigo_transacao', 'comprovante'),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('motivo', 'observacao'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('criado_por', 'data_solicitacao', 'atualizado_em', 'historico'),
            'classes': ('collapse',)
        }),
    )
    
    def valor_formatado(self, obj):
        return f"R$ {obj.valor:,.2f}"
    valor_formatado.short_description = 'Valor'
    valor_formatado.admin_order_field = 'valor'
    
    def status_badge(self, obj):
        cores = {
            'pendente': '#f6c23e',
            'aprovada': '#36b9cc',
            'realizada': '#1cc88a',
            'cancelada': '#e74a3b',
            'expirada': '#858796',
        }
        cor = cores.get(obj.status, '#858796')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; border-radius:12px; font-size:11px;">{}</span>',
            cor, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)
    
    def dias_vigencia(self, obj):
        return f"{obj.dias_vigencia} dias"
    dias_vigencia.short_description = 'Dias de Vigência'
    
    def is_vigente(self, obj):
        if obj.is_vigente:
            return format_html('<span style="color:#1cc88a;">✓ Vigente</span>')
        elif obj.is_expirada:
            return format_html('<span style="color:#e74a3b;">✗ Expirada</span>')
        return format_html('<span style="color:#858796;">— Futura</span>')
    is_vigente.short_description = 'Vigência'
    
    actions = ['aprovar_recargas', 'marcar_realizadas']
    
    @admin.action(description='Aprovar recargas selecionadas')
    def aprovar_recargas(self, request, queryset):
        count = queryset.filter(status='pendente').update(status='aprovada')
        self.message_user(request, f'{count} recarga(s) aprovada(s).')
    
    @admin.action(description='Marcar como realizadas')
    def marcar_realizadas(self, request, queryset):
        count = queryset.filter(status__in=['pendente', 'aprovada']).update(status='realizada')
        self.message_user(request, f'{count} recarga(s) marcada(s) como realizada(s).')



