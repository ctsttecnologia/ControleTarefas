from django.contrib import admin
from django.http import JsonResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
import requests
from .models import Logradouro
from .constant import ESTADOS_BRASIL
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin

@admin.register(Logradouro)
class LogradouroAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
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
    readonly_fields = ('data_cadastro', 'data_atualizacao', 'coordenadas_admin', 'filial',) # Impede a edição da filial após a criação.)
    
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
    
 # Adiciona a funcionalidade de autocompletar por CEP
    
def consulta_cep(request):
    """
    View para consultar um CEP na API ViaCEP e retornar os dados do endereço.
    """
    cep = request.GET.get('cep', '').replace('-', '').replace('.', '')

    if not cep.isdigit() or len(cep) != 8:
        return JsonResponse({'erro': 'CEP inválido. Deve conter 8 dígitos numéricos.'}, status=400)

    try:
        response = requests.get(f'https://viacep.com.br/ws/{cep}/json/')
        response.raise_for_status()  # Lança um erro para respostas HTTP 4xx/5xx
        data = response.json()

        if data.get('erro'):
            return JsonResponse({'erro': 'CEP não encontrado.'}, status=404)

        # Mapeia os campos da API ViaCEP para os campos do seu modelo/formulário
        endereco_data = {
            'endereco': data.get('logradouro', ''),
            'bairro': data.get('bairro', ''),
            'cidade': data.get('localidade', ''),
            'estado': data.get('uf', ''),
        }
        return JsonResponse(endereco_data)

    except requests.exceptions.RequestException as e:
        return JsonResponse({'erro': f'Erro ao consultar o serviço de CEP: {e}'}, status=500)
    except Exception as e:
        return JsonResponse({'erro': f'Ocorreu um erro inesperado: {e}'}, status=500)

