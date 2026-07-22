
# relatorio_fotografico/admin.py
from django.contrib import admin
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin
from .models import RelatorioFotografico, FotoRelatorio


class FotoRelatorioInline(admin.TabularInline):
    model = FotoRelatorio
    extra = 0
    fields = ['imagem', 'legenda', 'ordem']


@admin.register(RelatorioFotografico)
class RelatorioFotograficoAdmin(
    ChangeFilialAdminMixin, AdminFilialScopedMixin, admin.ModelAdmin
):
    list_display = ['titulo', 'obra_contrato', 'data', 'responsavel', 'filial', 'status', 'assunto']
    list_filter = ['status', 'filial', 'data']
    search_fields = ['titulo', 'obra_contrato', 'assunto']
    inlines = [FotoRelatorioInline]
    autocomplete_fields = ['responsavel', 'filial']


