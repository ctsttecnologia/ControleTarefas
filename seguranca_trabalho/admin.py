from django.contrib import admin
from django.utils.html import format_html
from .models import (EquipamentosSeguranca)


@admin.register(EquipamentosSeguranca)
class EquipamentosSegurancaAdmin(admin.ModelAdmin):
    list_display = ('nome_equioamento', 'tipo', 'codigo_ca', 'quantidade_estoque', 'ativo')
    list_filter = ('tipo', 'ativo')
    search_fields = ('nome_equioamento', 'codigo_ca')
