
# suprimentos/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Parceiro, Material, Contrato, VerbaContrato,
    Pedido, ItemPedido, AnexoPedido, HistoricoPedido,
    SolicitacaoCompra, AnexoSolicitacao, HistoricoSolicitacao,
    ItemSolicitacao, Cotacao, PedidoCompra, ItemPedidoCompra,
    EstoqueConsumo,
)


# ── Inlines ───────────────────────────────────────────────────
class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 1
    readonly_fields = ("valor_total", "custo_real", "total_creditos", "total_impostos")


class AnexoPedidoInline(admin.TabularInline):
    model = AnexoPedido
    extra = 0
    readonly_fields = ("criado_em",)


class HistoricoPedidoInline(admin.TabularInline):
    model = HistoricoPedido
    extra = 0
    readonly_fields = ("versao", "descricao", "responsavel", "status_anterior", "status_novo", "criado_em")
    can_delete = False


class ItemSolicitacaoInline(admin.TabularInline):
    model = ItemSolicitacao
    extra = 0
    readonly_fields = ("valor_total_estimado",)


class CotacaoInline(admin.TabularInline):
    model = Cotacao
    extra = 0
    readonly_fields = ("valor_total", "is_menor_preco")


class ItemPedidoCompraInline(admin.TabularInline):
    model = ItemPedidoCompra
    extra = 0
    readonly_fields = ("valor_total", "saldo_receber")


# ── Parceiro ──────────────────────────────────────────────────
@admin.register(Parceiro)
class ParceiroAdmin(admin.ModelAdmin):
    list_display = ("nome_fantasia", "razao_social", "cnpj", "eh_fornecedor", "eh_fabricante", "ativo")
    list_filter = ("eh_fornecedor", "eh_fabricante", "ativo", "filial")
    search_fields = ("nome_fantasia", "razao_social", "cnpj")
    list_per_page = 30


# ── Material ──────────────────────────────────────────────────
@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descricao", "classificacao", "tipo", "unidade", "valor_unitario", "ativo")
    list_filter = ("classificacao", "tipo", "ativo", "filial")
    search_fields = ("codigo", "descricao", "marca")
    readonly_fields = ("codigo",)
    list_per_page = 40


# ── Pedido ────────────────────────────────────────────────────
@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("numero", "contrato", "status_badge", "solicitante", "valor_total", "data_pedido")
    list_filter = ("status", "tipo_obra", "filial")
    search_fields = ("numero", "contrato__cm", "contrato__cliente")
    readonly_fields = ("numero", "data_pedido", "valor_total", "estoque_processado")
    inlines = [ItemPedidoInline, AnexoPedidoInline, HistoricoPedidoInline]
    #date_hierarchy = "data_pedido"

    @admin.display(description="Status")
    def status_badge(self, obj):
        cores = {
            "RASCUNHO": "secondary", "PENDENTE": "warning", "REVISAO": "info",
            "APROVADO": "success", "REPROVADO": "danger",
            "SOLICITACAO_GERADA": "primary", "CANCELADO": "dark",
        }
        cor = cores.get(obj.status, "secondary")
        return format_html('<span class="badge bg-{}">{}</span>', cor, obj.get_status_display())


# ── Solicitação de Compra ─────────────────────────────────────
@admin.register(SolicitacaoCompra)
class SolicitacaoCompraAdmin(admin.ModelAdmin):
    list_display = ("numero", "contrato", "status", "comprador", "valor_pedido", "criado_em")
    list_filter = ("status", "tipo_obra", "filial", "usa_novo_fluxo")
    search_fields = ("numero", "descricao_material", "contrato__cm")
    readonly_fields = ("numero", "criado_em", "atualizado_em")
    inlines = [ItemSolicitacaoInline]


@admin.register(ItemSolicitacao)
class ItemSolicitacaoAdmin(admin.ModelAdmin):
    list_display = ("material", "quantidade", "solicitacao", "status", "total_cotacoes")
    list_filter = ("status",)
    search_fields = ("material__descricao", "solicitacao__numero")
    inlines = [CotacaoInline]


@admin.register(Cotacao)
class CotacaoAdmin(admin.ModelAdmin):
    list_display = ("fornecedor", "valor_unitario", "valor_total", "prazo_entrega_dias", "is_menor_preco")
    list_filter = ("fornecedor",)
    search_fields = ("fornecedor__nome_fantasia", "item_solicitacao__material__descricao")


# ── Pedido de Compra ──────────────────────────────────────────
@admin.register(PedidoCompra)
class PedidoCompraAdmin(admin.ModelAdmin):
    list_display = ("numero", "numero_pedido", "fornecedor", "status", "valor_total", "data_emissao")
    list_filter = ("status", "filial", "tipo_nota_fiscal")
    search_fields = ("numero", "numero_pedido", "fornecedor__nome_fantasia")
    readonly_fields = ("numero", "valor_total")
    inlines = [ItemPedidoCompraInline]


@admin.register(EstoqueConsumo)
class EstoqueConsumoAdmin(admin.ModelAdmin):
    list_display = ("material", "contrato", "tipo", "quantidade", "responsavel", "criado_em")
    list_filter = ("tipo", "filial", "contrato")
    search_fields = ("material__descricao",)

# ── Contrato e Verba Contrato ──────────────────────────────────────────

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ("cm", "cliente", "filial", "ativo", "atualizado_em")
    list_filter = ("ativo", "filial")
    search_fields = ("cm", "cliente")
    list_select_related = ("filial",)
    ordering = ("cm",)
    readonly_fields = ("criado_em", "atualizado_em")
    fieldsets = (
        (None, {"fields": ("cm", "cliente", "filial", "ativo")}),
        ("Auditoria", {
            "classes": ("collapse",),
            "fields": ("criado_em", "atualizado_em"),
        }),
    )


@admin.register(VerbaContrato)
class VerbaContratoAdmin(admin.ModelAdmin):
    list_display = (
        "contrato", "ano", "mes",
        "verba_epi", "verba_consumo", "verba_ferramenta",
        "verba_total_col", "compra_total_col", "saldo_total_col",
    )
    list_filter = ("ano", "mes", "contrato__filial")
    search_fields = ("contrato__cm", "contrato__cliente")
    list_select_related = ("contrato",)
    ordering = ("-ano", "-mes")
    autocomplete_fields = ("contrato",)

    @admin.display(description="Verba Total")
    def verba_total_col(self, obj):
        return f"R$ {obj.verba_total:.2f}"

    @admin.display(description="Compra Total")
    def compra_total_col(self, obj):
        return f"R$ {obj.compra_total:.2f}"

    @admin.display(description="Saldo")
    def saldo_total_col(self, obj):
        cor = "green" if obj.saldo_total >= 0 else "red"
        return format_html(
            '<b style="color:{}">R$ {}</b>', cor, f"{obj.saldo_total:.2f}"
        )


admin.site.register([AnexoPedido, AnexoSolicitacao, HistoricoPedido, HistoricoSolicitacao, ItemPedidoCompra])
