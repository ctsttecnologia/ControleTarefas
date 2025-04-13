from django.contrib import admin
from .models import Logradouro
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .constant import ESTADOS_BRASIL

@admin.register(Logradouro)
class LogradouroAdmin(admin.ModelAdmin):
    list_display = (
        'endereco_completo',
        'bairro_cidade_uf',
        'cep_formatado',
        'coordenadas_link',
        'data_cadastro_formatada'
    )
    
    list_filter = (
        'estado',
        'cidade',
        'bairro',
    )
    
    search_fields = (
        'endereco',
        'numero',
        'cep',
        'bairro',
        'cidade',
        'complemento'
    )
    
    list_select_related = True
    
    readonly_fields = (
        'data_cadastro',
        'data_atualizacao',
        'endereco_completo_admin',
        'coordenadas_admin'
    )
    
    fieldsets = (
        (_('Informações Básicas'), {
            'fields': (
                'endereco',
                'numero',
                'complemento',
                'bairro'
            )
        }),
        (_('Localização'), {
            'fields': (
                'cep',
                'cidade',
                'estado',
                'pais',
                'ponto_referencia'
            )
        }),
        (_('Coordenadas Geográficas'), {
            'fields': (
                'latitude',
                'longitude',
                'coordenadas_admin'
            ),
            'classes': ('collapse',)
        }),
        (_('Auditoria'), {
            'fields': (
                'data_cadastro',
                'data_atualizacao',
                'endereco_completo_admin'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'definir_brasil_como_pais',
        'adicionar_sao_paulo_a_cidades'
    ]
    
    # Métodos de exibição
    def endereco_completo(self, obj):
        return obj.get_endereco_completo()
    endereco_completo.short_description = _('Endereço Completo')
    
    def endereco_completo_admin(self, obj):
        return obj.get_endereco_completo()
    endereco_completo_admin.short_description = _('Endereço Completo')
    
    def bairro_cidade_uf(self, obj):
        return f"{obj.bairro}, {obj.cidade}/{obj.estado}"
    bairro_cidade_uf.short_description = _('Bairro/Cidade/UF')
    bairro_cidade_uf.admin_order_field = 'bairro'
    
    def cep_formatado(self, obj):
        return obj.cep_formatado
    cep_formatado.short_description = _('CEP')
    
    def coordenadas_link(self, obj):
        if obj.latitude and obj.longitude:
            url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            return format_html(
                '<a href="{}" target="_blank">Ver no mapa</a>',
                url
            )
        return _("Não disponível")
    coordenadas_link.short_description = _('Mapa')
    
    def coordenadas_admin(self, obj):
        if obj.latitude and obj.longitude:
            url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            return format_html(
                '{}<br><a href="{}" target="_blank">Abrir no Google Maps</a>',
                obj.coordenadas, url
            )
        return _("Não informado")
    coordenadas_admin.short_description = _('Coordenadas')
    
    def data_cadastro_formatada(self, obj):
        return obj.data_cadastro.strftime('%d/%m/%Y')
    data_cadastro_formatada.short_description = _('Cadastrado em')
    data_cadastro_formatada.admin_order_field = 'data_cadastro'
    
    # Ações personalizadas
    def definir_brasil_como_pais(self, request, queryset):
        updated = queryset.update(pais='Brasil')
        self.message_user(
            request,
            _('Definido Brasil como país para %d endereços') % updated
        )
    definir_brasil_como_pais.short_description = _('Definir Brasil como país')
    
    def adicionar_sao_paulo_a_cidades(self, request, queryset):
        for logradouro in queryset.filter(estado='SP'):
            if 'São Paulo' not in logradouro.cidade:
                logradouro.cidade = f"São Paulo - {logradouro.cidade}"
                logradouro.save()
        self.message_user(
            request,
            _('Cidades de SP atualizadas com "São Paulo"')
        )
    adicionar_sao_paulo_a_cidades.short_description = _('Padronizar cidades de SP')
    
    # Formulário
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'estado':
            kwargs['choices'] = ESTADOS_BRASIL
        return super().formfield_for_choice_field(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
