
# tributacao/admin.py

from django.contrib import admin
from .models import NCM, CFOP, CST, GrupoTributario, TributacaoFederal, TributacaoEstadual


# ══════════════════════════════════════════════════════
# INLINES
# ══════════════════════════════════════════════════════
class TributacaoFederalInline(admin.StackedInline):
    model = TributacaoFederal
    extra = 1
    max_num = 1
    fieldsets = (
        ("IPI", {
            "fields": ("cst_ipi", "aliquota_ipi"),
        }),
        ("PIS", {
            "fields": ("cst_pis", "aliquota_pis", "gera_credito_pis"),
        }),
        ("COFINS", {
            "fields": ("cst_cofins", "aliquota_cofins", "gera_credito_cofins"),
        }),
        ("Observações", {
            "fields": ("observacoes",),
            "classes": ("collapse",),
        }),
    )


class TributacaoEstadualInline(admin.TabularInline):
    model = TributacaoEstadual
    extra = 1
    fields = (
        "uf_origem", "uf_destino", "cst_icms", "aliquota_icms",
        "reducao_base_icms", "permite_credito", "tem_st", "aliquota_fcp", "ativo",
    )


# ══════════════════════════════════════════════════════
# ADMINS
# ══════════════════════════════════════════════════════
@admin.register(NCM)
class NCMAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descricao", "aliquota_ipi_padrao", "ativo")
    search_fields = ("codigo", "descricao")
    list_filter = ("ativo",)
    list_editable = ("ativo",)


@admin.register(CFOP)
class CFOPAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descricao", "tipo", "ativo")
    search_fields = ("codigo", "descricao")
    list_filter = ("tipo", "ativo")
    list_editable = ("ativo",)


@admin.register(CST)
class CSTAdmin(admin.ModelAdmin):
    list_display = ("tipo", "codigo", "descricao")
    search_fields = ("codigo", "descricao")
    list_filter = ("tipo",)


@admin.register(GrupoTributario)
class GrupoTributarioAdmin(admin.ModelAdmin):
    list_display = ("nome", "natureza", "cfop", "ncm", "filial", "ativo")
    search_fields = ("nome",)
    list_filter = ("natureza", "ativo", "filial")
    inlines = [TributacaoFederalInline, TributacaoEstadualInline]


@admin.register(TributacaoFederal)
class TributacaoFederalAdmin(admin.ModelAdmin):
    list_display = (
        "grupo", "aliquota_ipi", "aliquota_pis", "gera_credito_pis",
        "aliquota_cofins", "gera_credito_cofins",
    )
    search_fields = ("grupo__nome",)


@admin.register(TributacaoEstadual)
class TributacaoEstadualAdmin(admin.ModelAdmin):
    list_display = (
        "grupo", "uf_origem", "uf_destino", "aliquota_icms",
        "permite_credito", "tem_st", "ativo",
    )
    search_fields = ("grupo__nome",)
    list_filter = ("uf_origem", "uf_destino", "permite_credito", "tem_st", "ativo")

