# ferramentas/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin
from django.contrib.auth import get_user_model

from .models import (
    Atividade, Ferramenta, MalaFerramentas, Movimentacao,
    AssinaturaMovimentacao, TermoDeResponsabilidade, ItemTermo
)

User = get_user_model()


# =============================================================================
# INLINE: Ferramentas dentro de uma Mala (mantido)
# =============================================================================

class FerramentaInline(admin.TabularInline):
    model = Ferramenta
    extra = 0
    fields = ('nome', 'codigo_identificacao', 'status', 'link_para_ferramenta')
    readonly_fields = ('nome', 'codigo_identificacao', 'status', 'link_para_ferramenta')
    verbose_name = "Item na Mala"
    verbose_name_plural = "Itens na Mala"

    @admin.display(description="Acessar")
    def link_para_ferramenta(self, obj):
        url = reverse('admin:ferramentas_ferramenta_change', args=[obj.pk])
        return format_html('<a href="{}">Ver Detalhes</a>', url)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MalaFerramentas)
class MalaFerramentasAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'codigo_identificacao', 'status', 'filial', 'contagem_itens', 'qr_code_preview')
    list_filter = ('status', 'filial')
    search_fields = ('nome', 'codigo_identificacao')
    readonly_fields = ('qr_code_preview',)
    inlines = [FerramentaInline]

    fieldsets = (
        ('Informações Principais', {
            'fields': ('nome', 'filial', 'codigo_identificacao', 'status', 'qr_code_preview')
        }),
        ('Localização', {
            'fields': ('localizacao_padrao',)
        }),
    )

    @admin.display(description="QR Code")
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="100" />', obj.qr_code.url)
        return "Será gerado ao salvar"

    @admin.display(description="Nº de Itens")
    def contagem_itens(self, obj):
        return obj.itens.count()


@admin.register(Ferramenta)
class FerramentaAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'patrimonio', 'status', 'mala', 'filial', 'qr_code_preview')
    list_filter = ('status', 'fabricante_marca', 'modelo', 'data_aquisicao', 'filial', 'mala')
    search_fields = ('nome', 'patrimonio', 'codigo_identificacao')
    readonly_fields = ('qr_code_preview',)
    raw_id_fields = ('mala',)

    fieldsets = (
        ('Informações Principais', {
            'fields': ('nome', 'filial', 'patrimonio', 'codigo_identificacao', 'fabricante_marca', 'modelo', 'qr_code_preview')
        }),
        ('Status, Localização e Associação', {
            'fields': ('status', 'localizacao_padrao', 'data_aquisicao', 'mala')
        }),
        ('Outras Informações', {
            'classes': ('collapse',),
            'fields': ('observacoes',)
        }),
    )

    @admin.display(description="QR Code")
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="100" />', obj.qr_code.url)
        return "Será gerado ao salvar"


# =============================================================================
# INLINE: Assinaturas dentro de Movimentacao (NOVO — via core.AssinavelMixin)
# =============================================================================

class AssinaturaMovimentacaoInline(admin.TabularInline):
    """
    Exibe as assinaturas (retirada/devolução) vinculadas à movimentação.
    Somente leitura — assinaturas nunca devem ser editadas via admin
    (dado sensível / integridade probatória).
    """
    model = AssinaturaMovimentacao
    extra = 0
    fields = ('tipo', 'assinatura_preview', 'data_assinatura', 'ip_assinatura')
    readonly_fields = ('tipo', 'assinatura_preview', 'data_assinatura', 'ip_assinatura')
    verbose_name = "Assinatura"
    verbose_name_plural = "Assinaturas"

    @admin.display(description="Assinatura")
    def assinatura_preview(self, obj):
        if obj.assinatura_imagem:
            return format_html(
                '<img src="{}" width="150" height="50" style="border: 1px solid #ccc;" />',
                obj.assinatura_imagem.url
            )
        return "Não fornecida"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Movimentacao)
class MovimentacaoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('item_movimentado_link', 'retirado_por', 'data_retirada', 'esta_ativa', 'filial')
    list_filter = ('data_retirada', 'filial')
    search_fields = ('ferramenta__nome', 'mala__nome', 'retirado_por__username')

    # ❌ Removidos: assinatura_retirada_preview, assinatura_devolucao_preview
    #    (agora vêm do inline AssinaturaMovimentacaoInline)
    readonly_fields = (
        'ferramenta', 'mala', 'filial', 'retirado_por', 'data_retirada', 'data_devolucao_prevista',
        'condicoes_retirada', 'recebido_por', 'data_devolucao', 'condicoes_devolucao',
    )
    inlines = [AssinaturaMovimentacaoInline]

    fieldsets = (
        ('Item Movimentado', {
            'fields': ('ferramenta', 'mala')
        }),
        ('Dados da Retirada', {
            'fields': ('filial', 'retirado_por', 'data_retirada', 'data_devolucao_prevista', 'condicoes_retirada')
        }),
        ('Dados da Devolução', {
            'fields': ('recebido_por', 'data_devolucao', 'condicoes_devolucao')
        }),
    )

    @admin.display(description="Item Movimentado", ordering='ferramenta__nome')
    def item_movimentado_link(self, obj):
        item = obj.item_movimentado
        if isinstance(item, Ferramenta):
            url = reverse('admin:ferramentas_ferramenta_change', args=[item.pk])
            return format_html('<b>Ferramenta:</b> <a href="{}">{}</a>', url, item)
        if isinstance(item, MalaFerramentas):
            url = reverse('admin:ferramentas_malaferramentas_change', args=[item.pk])
            return format_html('<b>Mala:</b> <a href="{}">{}</a>', url, item)
        return "N/A"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Atividade)
class AtividadeAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('timestamp', 'item_afetado', 'tipo_atividade', 'usuario', 'filial')
    list_filter = ('tipo_atividade', 'timestamp', 'filial')
    search_fields = ('ferramenta__nome', 'mala__nome', 'descricao', 'usuario__username')
    readonly_fields = ('timestamp', 'ferramenta', 'mala', 'tipo_atividade', 'descricao', 'usuario', 'filial')

    @admin.display(description="Item Afetado")
    def item_afetado(self, obj):
        return obj.ferramenta or obj.mala or "N/A"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# TERMOS DE RESPONSABILIDADE (adaptado ao AssinavelMixin)
# =============================================================================

class ItemTermoInline(admin.TabularInline):
    model = ItemTermo
    extra = 1
    fields = ['quantidade', 'unidade', 'item', 'ferramenta', 'mala']


@admin.register(TermoDeResponsabilidade)
class TermoDeResponsabilidadeAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    inlines = [ItemTermoInline]

    list_display = ('id', 'responsavel', 'contrato', 'data_emissao', 'is_signed', 'filial')
    list_filter = ('filial', 'tipo_uso', 'data_emissao')
    search_fields = ('responsavel__nome_completo', 'contrato')

    # token_assinatura removido (agora vive em TokenAssinaturaRemota, genérico, no core)
    # assinatura_imagem/data_assinatura/ip_assinatura vêm do AssinavelMixin
    readonly_fields = ('assinatura_preview', 'data_assinatura', 'ip_assinatura', 'movimentado_por')

    fieldsets = (
        ('Informações do Termo', {
            'fields': ('tipo_uso', 'contrato', 'responsavel', 'separado_por', 'data_emissao', 'filial')
        }),
        ('Controle de Assinatura (Gerado pelo Sistema)', {
            'classes': ('collapse',),
            'fields': ('assinatura_preview', 'data_assinatura', 'ip_assinatura', 'movimentado_por')
        }),
    )

    @admin.display(description="Assinatura")
    def assinatura_preview(self, obj):
        if obj.assinatura_imagem:
            return format_html(
                '<img src="{}" width="150" height="50" style="border: 1px solid #ccc;" />',
                obj.assinatura_imagem.url
            )
        return "Não fornecida"

    @admin.display(description="Assinado?", boolean=True)
    def is_signed(self, obj):
        return obj.is_signed()

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.movimentado_por = request.user
        super().save_model(request, obj, form, change)
