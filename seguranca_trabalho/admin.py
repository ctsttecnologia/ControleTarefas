# seguranca_trabalho/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Fabricante, Fornecedor, Funcao, Equipamento,
    MatrizEPI, FichaEPI, EntregaEPI, MovimentacaoEstoque
)
# REATORADO: Importa o mixin correto para o Admin.
from core.mixins import FilialAdminScopedMixin, ChangeFilialAdminMixin

# ... (Ações e Inlines permanecem os mesmos) ...

# Define MatrizEPIInline for use in FuncaoAdmin
from django.contrib.admin import TabularInline
from .models import MatrizEPI, EntregaEPI

class MatrizEPIInline(TabularInline):
    model = MatrizEPI
    extra = 0

# Define EntregaEPIInline for use in FichaEPIAdmin
class EntregaEPIInline(TabularInline):
    model = EntregaEPI
    extra = 0

# =============================================================================
# MODEL ADMINS
# =============================================================================

@admin.register(Fabricante)
# REATORADO: Usa FilialAdminScopedMixin e ajusta campos.
class FabricanteAdmin(FilialAdminScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'filial', 'cnpj', 'ativo')
    list_filter = ('ativo',) # 'filial' removido, pois o mixin já filtra.
    search_fields = ('nome', 'cnpj')
    readonly_fields = ('filial',) # Impede a edição da filial após a criação.

@admin.register(Fornecedor)
# REATORADO: Usa FilialAdminScopedMixin e ajusta campos.
class FornecedorAdmin(FilialAdminScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome_fantasia', 'filial', 'razao_social', 'cnpj', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome_fantasia', 'razao_social', 'cnpj')
    readonly_fields = ('filial',)

@admin.register(Funcao)
# REATORADO: Usa FilialAdminScopedMixin e ajusta campos.
class FuncaoAdmin(FilialAdminScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    inlines = [MatrizEPIInline]
    list_display = ('nome', 'filial', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome',)
    readonly_fields = ('filial',)

@admin.register(Equipamento)
# REATORADO: Usa FilialAdminScopedMixin e ajusta campos.
class EquipamentoAdmin(FilialAdminScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'filial', 'modelo', 'fabricante', 'data_validade_ca', 'ativo')
    list_filter = ('ativo', 'fabricante', 'requer_numero_serie')
    search_fields = ('nome', 'modelo', 'certificado_aprovacao', 'fabricante__nome')
    autocomplete_fields = ['fabricante', 'fornecedor_padrao']
    readonly_fields = ('filial',)
    fieldsets = (
        (None, {
            'fields': (
                'filial', 'nome', 'modelo', 'fabricante', 'fornecedor_padrao',
                'certificado_aprovacao', 'data_validade_ca', 'vida_util_dias',
                'estoque_minimo', 'requer_numero_serie', 'foto', 'observacoes', 'ativo'
            )
        }),
    )

@admin.register(FichaEPI)
# REATORADO: Usa FilialAdminScopedMixin e adiciona lógica customizada para salvar.
class FichaEPIAdmin(FilialAdminScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    inlines = [EntregaEPIInline]
    list_display = ('funcionario', 'filial', 'get_funcionario_cargo', 'atualizado_em')
    list_select_related = ('funcionario', 'funcionario__cargo', 'filial')
    search_fields = ('funcionario__nome_completo', 'funcionario__matricula')
    autocomplete_fields = ['funcionario']
    readonly_fields = ('filial', 'data_admissao', 'funcao', 'criado_em', 'atualizado_em')
    list_filter = ('funcionario__cargo',)
    
    #  Lógica customizada para atribuir a filial baseada no funcionário.
    def save_model(self, request, obj, form, change):
        # Se o funcionário foi definido, a filial da ficha DEVE ser a mesma.
        if obj.funcionario:
            obj.filial = obj.funcionario.filial
        super().save_model(request, obj, form, change)

    @admin.display(description=_('Cargo'), ordering='funcionario__cargo__nome')
    def get_funcionario_cargo(self, obj):

        return obj.funcionario.cargo.nome if obj.funcionario and obj.funcionario.cargo else "N/A"

@admin.register(EntregaEPI)
# Usa FilialAdminScopedMixin e ajusta campos.
class EntregaEPIAdmin(FilialAdminScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('ficha', 'filial', 'equipamento', 'data_entrega', 'status_da_entrega')
    list_filter = ('equipamento', 'data_entrega', 'data_devolucao')
    search_fields = ('equipamento__nome', 'ficha__funcionario__nome_completo')
    autocomplete_fields = ['ficha', 'equipamento']
    readonly_fields = ('filial', 'criado_em',)

    # Lógica customizada para herdar a filial da Ficha de EPI.
    def save_model(self, request, obj, form, change):
        if obj.ficha:
            obj.filial = obj.ficha.filial
        super().save_model(request, obj, form, change)
    
    @admin.display(description=_('Status'))
    def status_da_entrega(self, obj):
        return obj.status

@admin.register(MovimentacaoEstoque)
# Usa FilialAdminScopedMixin e ajusta campos.
class MovimentacaoEstoqueAdmin(FilialAdminScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('data', 'filial', 'equipamento', 'tipo', 'quantidade', 'responsavel')
    list_filter = ('tipo', 'equipamento', 'responsavel')
    search_fields = ('equipamento__nome', 'responsavel__username', 'justificativa')
    autocomplete_fields = ['equipamento', 'responsavel', 'fornecedor', 'entrega_associada']
    readonly_fields = ('filial', 'data',)
