# ferramentas/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin
# Importa o modelo MalaFerramentas
from .models import Atividade, Ferramenta, MalaFerramentas, Movimentacao


#  Inline para mostrar as ferramentas DENTRO de uma Mala
class FerramentaInline(admin.TabularInline):
    """Permite visualizar e editar as ferramentas que pertencem a uma mala."""
    model = Ferramenta
    extra = 0  # Não mostra formulários extras para adicionar novas
    fields = ('nome', 'codigo_identificacao', 'status', 'link_para_ferramenta')
    readonly_fields = ('nome', 'codigo_identificacao', 'status', 'link_para_ferramenta')
    verbose_name = "Item na Mala"
    verbose_name_plural = "Itens na Mala"

    @admin.display(description="Acessar")
    def link_para_ferramenta(self, obj):
        url = reverse('admin:ferramentas_ferramenta_change', args=[obj.pk])
        return format_html('<a href="{}">Ver Detalhes</a>', url)

    def has_add_permission(self, request, obj=None):
        return False # A adição de ferramentas a uma mala deve ser feita na própria ferramenta

    def has_delete_permission(self, request, obj=None):
        return False # A remoção também


# Registro completo para o modelo MalaFerramentas
@admin.register(MalaFerramentas)
class MalaFerramentasAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'codigo_identificacao', 'status', 'filial', 'contagem_itens', 'qr_code_preview')
    list_filter = ('status', 'filial')
    search_fields = ('nome', 'codigo_identificacao')
    readonly_fields = ('qr_code_preview',)
    inlines = [FerramentaInline] # Adiciona o inline de ferramentas aqui

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

#  FerramentaAdmin agora mostra a qual mala pertence
@admin.register(Ferramenta)
class FerramentaAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    # Adicionado 'mala' ao list_display e list_filter
    list_display = ('nome', 'patrimonio', 'status', 'mala', 'filial', 'qr_code_preview')
    list_filter = ('status', 'fabricante_marca', 'modelo', 'data_aquisicao', 'filial', 'mala')
    search_fields = ('nome', 'patrimonio', 'codigo_identificacao')
    readonly_fields = ('qr_code_preview',) # 'filial' removido daqui para ser editável se necessário
    
    #  Usando raw_id_fields para o campo 'mala' para melhor performance
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

#  MovimentacaoAdmin agora mostra o item correto (Ferramenta ou Mala)
@admin.register(Movimentacao)
class MovimentacaoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    # 'item_movimentado_link' substitui 'ferramenta'
    list_display = ('item_movimentado_link', 'retirado_por', 'data_retirada', 'esta_ativa', 'filial')
    list_filter = ('data_retirada', 'filial')
    # Busca por nome da ferramenta ou da mala
    search_fields = ('ferramenta__nome', 'mala__nome', 'retirado_por__username')
    readonly_fields = (
        'ferramenta', 'mala', 'filial', 'retirado_por', 'data_retirada', 'data_devolucao_prevista',
        'condicoes_retirada', 'assinatura_retirada_preview', 'recebido_por',
        'data_devolucao', 'condicoes_devolucao', 'assinatura_devolucao_preview'
    )
    fieldsets = (
        ('Item Movimentado', {
            'fields': ('ferramenta', 'mala')
        }),
        ('Dados da Retirada', {
            'fields': ('filial', 'retirado_por', 'data_retirada', 'data_devolucao_prevista', 'condicoes_retirada', 'assinatura_retirada_preview')
        }),
        ('Dados da Devolução', {
            'fields': ('recebido_por', 'data_devolucao', 'condicoes_devolucao', 'assinatura_devolucao_preview')
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

# [ATUALIZADO] AtividadeAdmin agora mostra o item correto (Ferramenta ou Mala)
@admin.register(Atividade)
class AtividadeAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    # [MELHORIA] 'item_afetado' substitui 'ferramenta'
    list_display = ('timestamp', 'item_afetado', 'tipo_atividade', 'usuario', 'filial')
    list_filter = ('tipo_atividade', 'timestamp', 'filial')
    search_fields = ('ferramenta__nome', 'mala__nome', 'descricao', 'usuario__username')
    readonly_fields = ('timestamp', 'ferramenta', 'mala', 'tipo_atividade', 'descricao', 'usuario', 'filial')

    @admin.display(description="Item Afetado")
    def item_afetado(self, obj):
        return obj.ferramenta or obj.mala or "N/A"

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    