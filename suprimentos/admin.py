
# suprimentos/admin.py

from django.contrib import admin
from .models import Parceiro

@admin.register(Parceiro)
class ParceiroAdmin(admin.ModelAdmin):
    list_display = ('nome_fantasia', 'razao_social', 'cnpj', 'eh_fabricante', 'eh_fornecedor', 'ativo')
    list_filter = ('filial', 'eh_fabricante', 'eh_fornecedor', 'ativo')
    
    # A LINHA MAIS IMPORTANTE PARA O AUTOCOMPLETE:
    search_fields = ('nome_fantasia', 'razao_social', 'cnpj')
    autocomplete_fields = ['endereco']
    readonly_fields = ('filial',)
