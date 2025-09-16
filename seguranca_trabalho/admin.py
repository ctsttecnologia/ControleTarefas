# seguranca_trabalho/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Fabricante, Fornecedor, Funcao, Equipamento,
    MatrizEPI, FichaEPI, EntregaEPI, MovimentacaoEstoque
)
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin
from django.contrib.admin import TabularInline
from .models import MatrizEPI, EntregaEPI


class MatrizEPIInline(TabularInline):
    model = MatrizEPI
    extra = 1
    autocomplete_fields = ['equipamento']
    readonly_fields = ('filial',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filtra os equipamentos para a filial da função sendo editada
        if db_field.name == "equipamento":
            # Tenta obter a filial do objeto (função) que está sendo editado
            # O request pode não ter o object_id em todos os casos (ex: ao adicionar)
            # Esta é uma abordagem que funciona na edição.
            # Para o 'add', a filtragem pode não funcionar como esperado sem JS.
            if request._obj_ is not None:
                kwargs["queryset"] = Equipamento.objects.filter(filial=request._obj_.filial)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # Armazena o objeto (função) no request para uso no formfield_for_foreignkey
        request._obj_ = obj
        return super().get_formset(request, obj, **kwargs)


class EntregaEPIInline(TabularInline):
    model = EntregaEPI
    extra = 1
    autocomplete_fields = ['equipamento']
    readonly_fields = ('filial', 'criado_em',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filtra os equipamentos para a filial da ficha de EPI
        if db_field.name == "equipamento":
            if request._obj_ is not None:
                kwargs["queryset"] = Equipamento.objects.filter(filial=request._obj_.filial)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # Armazena o objeto (ficha) no request
        request._obj_ = obj
        return super().get_formset(request, obj, **kwargs)


@admin.register(MatrizEPI)
class MatrizEPIAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    """
    Admin para gerenciar todas as entradas da Matriz de EPI de forma centralizada.
    """
    list_display = ('funcao', 'equipamento', 'filial', 'frequencia_troca_meses')
    list_filter = ('filial', 'funcao', 'equipamento')
    search_fields = ('funcao__nome', 'equipamento__nome')
    autocomplete_fields = ['funcao', 'equipamento']
    list_select_related = ('funcao', 'equipamento', 'filial') # Otimiza a consulta

    # Lógica para garantir que a filial seja herdada da função
    def save_model(self, request, obj, form, change):
        if obj.funcao:
            obj.filial = obj.funcao.filial
        super().save_model(request, obj, form, change)

@admin.register(EntregaEPI)
# Usa FilialAdminScopedMixin e ajusta campos.
class EntregaEPIAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
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

# =============================================================================
# MODEL ADMINS
# =============================================================================

@admin.register(Fabricante)
# REATORADO: Usa FilialAdminScopedMixin e ajusta campos.
class FabricanteAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'filial', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'cnpj')
    

@admin.register(Fornecedor)
# REATORADO: Usa FilialAdminScopedMixin e ajusta campos.
class FornecedorAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome_fantasia', 'filial', 'razao_social', 'cnpj', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome_fantasia', 'razao_social', 'cnpj')
    

@admin.register(Funcao)
# REATORADO: Usa FilialAdminScopedMixin e ajusta campos.
class FuncaoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    inlines = [MatrizEPIInline]
    list_display = ('nome', 'filial', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome',)
    readonly_fields = ('filial',)

    def get_form(self, request, obj=None, **kwargs):
        # Armazena o objeto (função) no request para uso nos inlines
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

@admin.register(Equipamento)
# REATORADO: Usa FilialAdminScopedMixin e ajusta campos.
class EquipamentoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'filial', 'modelo', 'fabricante', 'data_validade_ca', 'ativo', 'data_cadastro')
    list_filter = ('ativo', 'fabricante', 'requer_numero_serie', 'data_cadastro')
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
# Usa FilialAdminScopedMixin e adiciona lógica customizada para salvar.
class FichaEPIAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    inlines = [EntregaEPIInline]
    list_display = ('funcionario', 'filial', 'get_funcionario_cargo', 'atualizado_em')
    list_select_related = ('funcionario', 'funcionario__cargo', 'filial')
    search_fields = ('funcionario__nome_completo', 'funcionario__matricula')
    autocomplete_fields = ['funcionario']
    readonly_fields = ('filial', 'data_admissao', 'funcao', 'criado_em', 'atualizado_em')
    list_filter = ('funcionario__cargo',)
    
    def get_form(self, request, obj=None, **kwargs):
        # Armazena o objeto (ficha) no request para uso nos inlines
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

    #  Lógica customizada para atribuir a filial baseada no funcionário.
    def save_model(self, request, obj, form, change):
        # Se o funcionário foi definido, a filial da ficha DEVE ser a mesma.
        if obj.funcionario:
            obj.filial = obj.funcionario.filial
        super().save_model(request, obj, form, change)

    @admin.display(description=_('Cargo'), ordering='funcionario__cargo__nome')
    def get_funcionario_cargo(self, obj):

        return obj.funcionario.cargo.nome if obj.funcionario and obj.funcionario.cargo else "N/A"

@admin.register(MovimentacaoEstoque)
# Usa FilialAdminScopedMixin e ajusta campos.
class MovimentacaoEstoqueAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('data', 'filial', 'equipamento', 'tipo', 'quantidade', 'responsavel')
    list_filter = ('tipo', 'equipamento', 'responsavel')
    search_fields = ('equipamento__nome', 'responsavel__username', 'justificativa')
    autocomplete_fields = ['equipamento', 'responsavel', 'fornecedor', 'entrega_associada']
    readonly_fields = ('filial', 'data',)
