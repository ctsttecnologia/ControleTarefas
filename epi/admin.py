from django.contrib import admin
from django.utils.html import format_html
from .models import (EPI, FichaEPI, ItemEPI) 

@admin.register(EPI)
class EPIAdmin(admin.ModelAdmin):
    list_display = ('nome', 'certificado', 'unidade')
    search_fields = ('nome', 'certificado')
    list_filter = ('unidade',)

@admin.register(FichaEPI)
class FichaEPIAdmin(admin.ModelAdmin):
    list_display = ('empregado', 'cargo', 'admissao', 'contrato', 'assinatura_preview')
    list_filter = ('admissao', 'cargo')
    search_fields = ('empregado__username', 'contrato')
    raw_id_fields = ('empregado',)
    date_hierarchy = 'admissao'

    def assinatura_preview(self, obj):
        if obj.assinatura:
            return format_html('<img src="{}" width="50" height="auto" />', obj.assinatura.url)
        return "-"
    assinatura_preview.short_description = 'Assinatura'

@admin.register(ItemEPI)
class ItemEPIAdmin(admin.ModelAdmin):
    list_display = ('ficha', 'epi', 'quantidade', 'data_recebimento')
    list_filter = ('epi', 'data_recebimento')
    raw_id_fields = ('ficha', 'epi')
    date_hierarchy = 'data_recebimento'
