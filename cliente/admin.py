from django.contrib import admin
from django.utils.html import format_html
from .models import Cliente
from .models import ClienteCliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'logradouro', 'contrato', 'razao_social', 'cnpj', 'estatus')
    list_filter = ('logradouro', 'estatus', 'data_de_inicio')
    search_fields = ('nome', 'cnpj', 'razao_social')
    raw_id_fields = ('logradouro',)
    list_editable = ('estatus',)
    date_hierarchy = 'data_de_inicio'

@admin.register(ClienteCliente)
class ClienteClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cliente')
    list_filter = ('cliente',)
    raw_id_fields = ('cliente',)