
# suprimentos/admin.py
from django.contrib import admin

from .models import (
    Parceiro, Material, Contrato, VerbaContrato,
    Pedido, ItemPedido, AnexoPedido, HistoricoPedido,
    SolicitacaoCompra, AnexoSolicitacao, HistoricoSolicitacao,
)


# ═════════════════════════════════════════════════════════════════════════════
# PARCEIRO
# ═════════════════════════════════════════════════════════════════════════════

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


# ═════════════════════════════════════════════════════════════════════════════
# MATERIAL
# ═════════════════════════════════════════════════════════════════════════════

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
    readonly_fields = ['codigo', 'criado_em', 'atualizado_em']


# ═════════════════════════════════════════════════════════════════════════════
# CONTRATO  +  VERBA
# ═════════════════════════════════════════════════════════════════════════════

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


# ═════════════════════════════════════════════════════════════════════════════
# PEDIDO
# ═════════════════════════════════════════════════════════════════════════════

class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    fields = ['material', 'quantidade', 'valor_unitario', 'valor_total', 'observacao']
    readonly_fields = ['valor_total']
    autocomplete_fields = ['material']


class AnexoPedidoInline(admin.TabularInline):
    model = AnexoPedido
    extra = 0
    fields = ['arquivo', 'descricao', 'enviado_por', 'criado_em']
    readonly_fields = ['enviado_por', 'criado_em']


class HistoricoPedidoInline(admin.TabularInline):
    model = HistoricoPedido
    extra = 0
    can_delete = False
    fields = ['versao', 'descricao', 'responsavel',
              'status_anterior', 'status_novo', 'criado_em']
    readonly_fields = ['versao', 'descricao', 'responsavel',
                       'status_anterior', 'status_novo', 'criado_em']
    ordering = ['-versao']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'tipo_obra', 'contrato', 'solicitante',
        'status', 'data_pedido', 'aprovador', 'solicitacao_gerada',
    ]
    list_filter = ['status', 'tipo_obra', 'data_pedido', 'contrato__filial']
    search_fields = [
        'numero', 'contrato__cliente', 'contrato__cm', 'descricao_material',
    ]
    readonly_fields = [
        'numero', 'data_pedido', 'solicitacao_gerada',
        'criado_em', 'atualizado_em', 'estoque_processado',
    ]
    inlines = [ItemPedidoInline, AnexoPedidoInline, HistoricoPedidoInline]
    date_hierarchy = 'data_pedido'
    autocomplete_fields = ['contrato', 'solicitante', 'aprovador', 'recebedor']


# ═════════════════════════════════════════════════════════════════════════════
# SOLICITAÇÃO DE COMPRA
# ═════════════════════════════════════════════════════════════════════════════

class AnexoSolicitacaoInline(admin.TabularInline):
    model = AnexoSolicitacao
    extra = 0
    fields = ['arquivo', 'tipo_documento', 'descricao',
              'confidencial', 'enviado_por', 'criado_em']
    readonly_fields = ['enviado_por', 'criado_em']


class HistoricoSolicitacaoInline(admin.TabularInline):
    model = HistoricoSolicitacao
    extra = 0
    can_delete = False
    fields = ['versao', 'descricao', 'responsavel',
              'status_anterior', 'status_novo', 'criado_em']
    readonly_fields = ['versao', 'descricao', 'responsavel',
                       'status_anterior', 'status_novo', 'criado_em']
    ordering = ['-versao']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SolicitacaoCompra)
class SolicitacaoCompraAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'tipo_obra', 'contrato', 'solicitante',
        'comprador', 'status', 'criado_em',
    ]
    list_filter = ['status', 'tipo_obra', 'filial', 'tipo_insumo']
    search_fields = [
        'numero', 'descricao_material',
        'contrato__cm', 'contrato__cliente',
        'numero_pedido_sienge', 'numero_nota_fiscal',
    ]
    readonly_fields = ['numero', 'criado_em', 'atualizado_em']
    inlines = [AnexoSolicitacaoInline, HistoricoSolicitacaoInline]
    date_hierarchy = 'criado_em'
    list_per_page = 30
    autocomplete_fields = [
        'contrato', 'solicitante', 'aprovador_inicial',
        'comprador', 'aprovador_cotacao', 'aprovador_pedido',
        'fornecedor',
    ]

    fieldsets = (
        ('Identificação', {
            'fields': ('numero', 'filial', 'status', 'tipo_obra', 'contrato', 'pedido'),
        }),
        ('Material Solicitado', {
            'fields': ('descricao_material', 'quantidade', 'unidade_medida',
                       'tipo_insumo', 'data_necessaria'),
        }),
        ('Responsáveis', {
            'fields': ('solicitante', 'aprovador_inicial', 'comprador',
                       'aprovador_cotacao', 'aprovador_pedido'),
        }),
        ('Cotação', {
            'fields': ('data_cotacao', 'numero_cotacao', 'cnpj_compra', 'tipo_nota_fiscal'),
            'classes': ('collapse',),
        }),
        ('Validação', {
            'fields': ('data_validacao_cotacao',),
            'classes': ('collapse',),
        }),
        ('Pedido', {
            'fields': ('data_criacao_pedido', 'numero_pedido',
                       'fornecedor', 'valor_pedido', 'data_aprovacao_pedido'),
            'classes': ('collapse',),
        }),
        ('Entrega', {
            'fields': ('data_envio_fornecedor', 'data_prevista_entrega',
                       'data_entrega_efetiva', 'numero_nota_fiscal'),
            'classes': ('collapse',),
        }),
        ('Observações', {
            'fields': ('observacoes', 'motivo_cancelamento'),
        }),
        ('Datas do Sistema', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )


# ═════════════════════════════════════════════════════════════════════════════
# HISTÓRICO DA SOLICITAÇÃO (admin standalone)
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(HistoricoSolicitacao)
class HistoricoSolicitacaoAdmin(admin.ModelAdmin):
    list_display = ['solicitacao', 'versao', 'descricao', 'responsavel', 'criado_em']
    list_filter = ['solicitacao__status']
    search_fields = ['solicitacao__numero', 'descricao']
    readonly_fields = [
        'solicitacao', 'versao', 'descricao', 'responsavel',
        'status_anterior', 'status_novo', 'criado_em',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False