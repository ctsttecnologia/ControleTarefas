from django.contrib import admin
from django.utils.html import format_html
from .models import Ferramenta, Movimentacao, Atividade
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin

class AtividadeInline(admin.TabularInline):
    model = Atividade
    extra = 0
    fields = ('timestamp', 'tipo_atividade', 'descricao', 'usuario')
    readonly_fields = ('fields',)
    can_delete = False
    verbose_name = "Registro de Atividade"
    verbose_name_plural = "Registros de Atividades"

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Ferramenta)
class FerramentaAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'patrimonio', 'status', 'filial', 'qr_code_preview')
    list_filter = ('status', 'fabricante', 'filial')
    search_fields = ('nome', 'patrimonio', 'codigo_identificacao')
    readonly_fields = ('qr_code_preview', 'filial',) # Impede a edição da filial após a criação.)
    inlines = [AtividadeInline]
    fieldsets = (
        ('Informações Principais', {
            'fields': ('nome', 'filial', 'patrimonio', 'codigo_identificacao', 'fabricante', 'qr_code_preview')
        }),
        ('Status e Localização', {
            'fields': ('status', 'localizacao_padrao', 'data_aquisicao')
        }),
        ('Outras Informações', {
            'classes': ('collapse',),
            'fields': ('observacoes',)
        }),
    )

    @admin.display(description="QR Code")
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="100" height="100" />', obj.qr_code.url)
        return "Será gerado ao salvar"

@admin.register(Movimentacao)
class MovimentacaoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('ferramenta', 'retirado_por', 'data_retirada', 'esta_ativa', 'filial')
    list_filter = ('data_retirada', 'filial', 'ferramenta__nome')
    search_fields = ('ferramenta__nome', 'retirado_por__username')
    readonly_fields = (
        'ferramenta', 'filial', 'retirado_por', 'data_retirada', 'data_devolucao_prevista',
        'condicoes_retirada', 'assinatura_retirada_preview', 'recebido_por',
        'data_devolucao', 'condicoes_devolucao', 'assinatura_devolucao_preview'
    )
    fieldsets = (
        ('Dados da Retirada', {
            'fields': ('ferramenta', 'filial', 'retirado_por', 'data_retirada', 'data_devolucao_prevista', 'condicoes_retirada', 'assinatura_retirada_preview')
        }),
        ('Dados da Devolução', {
            'fields': ('recebido_por', 'data_devolucao', 'condicoes_devolucao', 'assinatura_devolucao_preview')
        }),
    )

    @admin.display(description="Assinatura (Retirada)")
    def assinatura_retirada_preview(self, obj):
        if obj.assinatura_retirada:
            return format_html('<img src="{}" width="150" height="50" style="border: 1px solid #ccc;" />', obj.assinatura_retirada.url)
        return "Não fornecida"

    @admin.display(description="Assinatura (Devolução)")
    def assinatura_devolucao_preview(self, obj):
        if obj.assinatura_devolucao:
            return format_html('<img src="{}" width="150" height="50" style="border: 1px solid #ccc;" />', obj.assinatura_devolucao.url)
        return "Não fornecida"

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Atividade)
class AtividadeAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('timestamp', 'ferramenta', 'tipo_atividade', 'usuario', 'filial')
    list_filter = ('tipo_atividade', 'timestamp', 'filial')
    search_fields = ('ferramenta__nome', 'descricao', 'usuario__username')
    readonly_fields = ('timestamp', 'ferramenta', 'tipo_atividade', 'descricao', 'usuario', 'filial')

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
