from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Logradouro
from .constant import ESTADOS_BRASIL
from core.admin import FilialAdminMixin

@admin.register(Logradouro)
class LogradouroAdmin(FilialAdminMixin, admin.ModelAdmin):
    list_display = (
        'endereco_completo',
        'filial',
        'bairro_cidade_uf',
        'cep_formatado',
        'coordenadas_link',
        'data_cadastro_formatada'
    )
    
    list_filter = ('estado', 'filial', 'cidade', 'bairro')
    search_fields = ('endereco', 'numero', 'cep', 'bairro', 'cidade')
    readonly_fields = ('data_cadastro', 'data_atualizacao', 'coordenadas_admin')
    
    fieldsets = (
        (_('Informações Básicas'), {
            'fields': ('endereco', 'numero', 'complemento', 'bairro')
        }),
        (_('Localização'), {
            'fields': ('cep', 'cidade', 'estado', 'pais', 'ponto_referencia')
        }),
        (_('Coordenadas'), {
            'fields': ('latitude', 'longitude', 'coordenadas_admin'),
            'classes': ('collapse',)
        }),
        (_('Auditoria'), {
            'fields': ('data_cadastro', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    def endereco_completo(self, obj):
        return obj.get_endereco_completo()
    endereco_completo.short_description = _('Endereço Completo')
    
    def bairro_cidade_uf(self, obj):
        return f"{obj.bairro}, {obj.cidade}/{obj.estado}"
    bairro_cidade_uf.short_description = _('Localização')
    
    def cep_formatado(self, obj):
        return obj.cep_formatado
    cep_formatado.short_description = _('CEP')
    
    def coordenadas_link(self, obj):
        if obj.latitude and obj.longitude:
            url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            return format_html('<a href="{}" target="_blank">Ver mapa</a>', url)
        return _("Não disponível")
    coordenadas_link.short_description = _('Mapa')
    
    def coordenadas_admin(self, obj):
        if obj.latitude and obj.longitude:
            return f"{obj.latitude}, {obj.longitude}"
        return _("Não informado")
    coordenadas_admin.short_description = _('Coordenadas')
    
    def data_cadastro_formatada(self, obj):
        return obj.data_cadastro.strftime('%d/%m/%Y')
    data_cadastro_formatada.short_description = _('Cadastrado em')
    
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'estado':
            kwargs['choices'] = ESTADOS_BRASIL
        return super().formfield_for_choice_field(db_field, request, **kwargs)
