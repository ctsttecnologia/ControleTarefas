
# suprimentos/admin.py

from django.contrib import admin
from .models import (
    Parceiro, Material, Contrato, VerbaContrato,
    Pedido, ItemPedido,
)


# ══════════════════════════════════════════════
# PARCEIRO (preservado)
# ══════════════════════════════════════════════
@admin.register(Parceiro)
class ParceiroAdmin(admin.ModelAdmin):
    list_display = (
        'nome_fantasia', 'razao_social', 'cnpj',
        'eh_fabricante', 'eh_fornecedor', 'ativo',
    )
    list_filter = ('filial', 'eh_fabricante', 'eh_fornecedor', 'ativo')
    search_fields = ('nome_fantasia', 'razao_social', 'cnpj')
    autocomplete_fields = ['endereco']
    readonly_fields = ('filial',)


# ══════════════════════════════════════════════
# MATERIAL
# ══════════════════════════════════════════════
@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'descricao', 'classificacao', 'tipo',
        'marca', 'unidade', 'valor_unitario', 'ativo',
    ]
    list_filter = ['classificacao', 'tipo', 'ativo']
    search_fields = ['descricao', 'marca', 'codigo']
    list_editable = ['valor_unitario', 'ativo']
    list_per_page = 50


# ══════════════════════════════════════════════
# CONTRATO + VERBAS
# ══════════════════════════════════════════════
class VerbaInline(admin.TabularInline):
    model = VerbaContrato
    extra = 1
    fields = ['ano', 'mes', 'verba_epi', 'verba_consumo', 'verba_ferramenta']


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ['cm', 'cliente', 'filial', 'ativo']
    list_filter = ['ativo', 'filial']
    search_fields = ['cm', 'cliente']
    inlines = [VerbaInline]


# ══════════════════════════════════════════════
# PEDIDO + ITENS
# ══════════════════════════════════════════════
class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ['valor_total']
    autocomplete_fields = ['material']


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'contrato', 'solicitante', 'status',
        'data_pedido', 'aprovador', 'recebedor',
    ]
    list_filter = ['status', 'data_pedido', 'contrato__filial']
    search_fields = ['numero', 'contrato__cliente', 'contrato__cm']
    readonly_fields = ['numero', 'data_pedido']
    inlines = [ItemPedidoInline]
