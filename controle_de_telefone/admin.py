
# aparelhos/admin.py
from django.contrib import admin
from .models import Marca, Modelo, Aparelho, Operadora, Plano, LinhaTelefonica, Vinculo

from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin




@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'criado_em')
    search_fields = ('nome',)

@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    list_display = ('nome', 'marca', 'criado_em')
    list_filter = ('marca',)
    search_fields = ('nome', 'marca__nome')

@admin.register(Aparelho)
class AparelhoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('__str__', 'filial', 'status', 'data_aquisicao')
    list_filter = ('status', 'filial', 'modelo__marca')
    search_fields = ('numero_serie', 'modelo__nome')
    readonly_fields = ('filial',) # A filial é definida na criação e não deve ser alterada
    list_select_related = ('modelo', 'modelo__marca', 'filial')

@admin.register(Operadora)
class OperadoraAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'operadora', 'valor_mensal', 'franquia_dados_gb')
    list_filter = ('operadora',)
    search_fields = ('nome', 'operadora__nome')

@admin.register(LinhaTelefonica)
class LinhaTelefonicaAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('numero', 'filial', 'plano', 'status', 'data_ativacao')
    list_filter = ('status', 'filial', 'plano__operadora')
    search_fields = ('numero',)
    readonly_fields = ('filial',)
    list_select_related = ('plano', 'plano__operadora', 'filial')


@admin.register(Vinculo)
class VinculoAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'aparelho', 'linha', 'data_entrega', 'data_devolucao', 'status')
    list_filter = ('status', 'funcionario__filial')
    search_fields = (
        'funcionario__nome_completo', 
        'aparelho__modelo__nome', 
        'aparelho__numero_serie', 
        'linha__numero'
    )
    autocomplete_fields = ['funcionario', 'aparelho', 'linha']
    list_select_related = ('funcionario', 'aparelho__modelo', 'linha')
    
    def get_queryset(self, request):
        # Filtra os vínculos pela filial ativa do usuário
        qs = super().get_queryset(request)
        filial_id = request.session.get('active_filial_id')
        if filial_id and not request.user.is_superuser:
            qs = qs.filter(funcionario__filial_id=filial_id)
        return qs



