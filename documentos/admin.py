from django.contrib import admin
from .models import Documento


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'status', 'data_vencimento', 'cliente', 'filial', 'is_anexado')
    list_filter = ('tipo', 'status', 'filial')
    search_fields = ('nome', 'descricao')
    readonly_fields = ('data_cadastro', 'data_atualizacao', 'content_type', 'object_id')

    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'tipo', 'descricao', 'arquivo'),
        }),
        ('Datas e Vencimento', {
            'fields': ('data_emissao', 'data_vencimento', 'dias_aviso', 'status'),
        }),
        ('Relacionamentos', {
            'fields': ('responsavel', 'cliente', 'filial'),
        }),
        ('Vínculo Genérico (se anexado a outro objeto)', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',),
        }),
        ('Renovação', {
            'fields': ('substitui',),
            'classes': ('collapse',),
        }),
        ('Auditoria', {
            'fields': ('data_cadastro', 'data_atualizacao'),
        }),
    )

    def is_anexado(self, obj):
        return obj.is_anexado
    is_anexado.boolean = True
    is_anexado.short_description = "Anexado?"
