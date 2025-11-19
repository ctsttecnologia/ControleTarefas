
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline
from documentos.models import Documento
from .models import Arquivo

# Permite editar o Documento (datas/arquivo) diretamente dentro do Admin do Arquivo
class DocumentoInline(GenericStackedInline):
    model = Documento
    extra = 0
    fields = ('arquivo', 'data_emissao', 'data_vencimento', 'responsavel', 'status')

@admin.register(Arquivo)
class ArquivoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'status', 'dias_aviso', 'filial')
    list_filter = ('tipo', 'status', 'filial')
    search_fields = ('nome', 'descricao')
    inlines = [DocumentoInline]
