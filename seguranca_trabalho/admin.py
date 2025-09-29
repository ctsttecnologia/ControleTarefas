# seguranca_trabalho/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Fabricante, Fornecedor, Funcao, Equipamento,
    MatrizEPI, FichaEPI, EntregaEPI, MovimentacaoEstoque
)
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin
from django.contrib.admin import TabularInline

# As classes Inline (MatrizEPIInline, EntregaEPIInline) estão corretas.
# Nenhuma alteração necessária aqui.
class MatrizEPIInline(TabularInline):
    model = MatrizEPI
    extra = 1
    autocomplete_fields = ['equipamento']
    readonly_fields = ('filial',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "equipamento":
            if hasattr(request, '_obj_') and request._obj_ is not None:
                # Garante que a filial exista no objeto antes de filtrar
                if hasattr(request._obj_, 'filial') and request._obj_.filial:
                    kwargs["queryset"] = Equipamento.objects.filter(filial=request._obj_.filial)
                else:
                    # Se o objeto pai (Funcao) ainda não tem filial (ex: na criação), não filtra
                    kwargs["queryset"] = Equipamento.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_formset(request, obj, **kwargs)


class EntregaEPIInline(TabularInline):
    model = EntregaEPI
    extra = 1
    autocomplete_fields = ['equipamento']
    readonly_fields = ('filial', 'criado_em',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "equipamento":
            if hasattr(request, '_obj_') and request._obj_ is not None:
                if hasattr(request._obj_, 'filial') and request._obj_.filial:
                    kwargs["queryset"] = Equipamento.objects.filter(filial=request._obj_.filial)
                else:
                    kwargs["queryset"] = Equipamento.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_formset(request, obj, **kwargs)

# O MatrizEPIAdmin está correto, pois depende da Funcao ter uma filial.
@admin.register(MatrizEPI)
class MatrizEPIAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('funcao', 'equipamento', 'filial', 'frequencia_troca_meses')
    list_filter = ('filial', 'funcao', 'equipamento')
    search_fields = ('funcao__nome', 'equipamento__nome')
    autocomplete_fields = ['funcao', 'equipamento']
    list_select_related = ('funcao', 'equipamento', 'filial')

    def save_model(self, request, obj, form, change):
        if obj.funcao:
            obj.filial = obj.funcao.filial
        super().save_model(request, obj, form, change)

# O EntregaEPIAdmin está correto.
@admin.register(EntregaEPI)
class EntregaEPIAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('ficha', 'filial', 'equipamento', 'data_entrega', 'status_da_entrega')
    list_filter = ('equipamento', 'data_entrega', 'data_devolucao')
    search_fields = ('equipamento__nome', 'ficha__funcionario__nome_completo')
    autocomplete_fields = ['ficha', 'equipamento']
    readonly_fields = ('filial', 'criado_em',)

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
class FabricanteAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'filial', 'ativo')
    list_filter = ('ativo', 'filial') # Adicionado filial ao filtro
    search_fields = ('nome', 'cnpj')
    
@admin.register(Fornecedor)
class FornecedorAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome_fantasia', 'filial', 'razao_social', 'cnpj', 'ativo')
    list_filter = ('ativo', 'filial') # Adicionado filial ao filtro
    search_fields = ('nome_fantasia', 'razao_social', 'cnpj')
    
@admin.register(Funcao)
class FuncaoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    inlines = [MatrizEPIInline]
    list_display = ('nome', 'filial', 'ativo')
    list_filter = ('ativo', 'filial') # Adicionado filial ao filtro para facilitar a administração
    search_fields = ('nome',)
    readonly_fields = ('filial',)

    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

    # ============================================================ #
    # == CORREÇÃO ADICIONADA AQUI ==
    # Define a filial automaticamente ao salvar, com base no usuário logado.
    # Essencial porque 'filial' é um campo readonly_fields.
    # ============================================================ #
    def save_model(self, request, obj, form, change):
        if not obj.filial_id: # Apenas se a filial não estiver definida
             active_filial = getattr(request.user, 'filial_ativa', None)
             if active_filial:
                 obj.filial = active_filial
        super().save_model(request, obj, form, change)

@admin.register(Equipamento)
class EquipamentoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'filial', 'modelo', 'fabricante', 'data_validade_ca', 'ativo', 'data_cadastro')
    list_filter = ('ativo', 'filial', 'fabricante', 'requer_numero_serie') # Adicionado filial
    search_fields = ('nome', 'modelo', 'certificado_aprovacao', 'fabricante__nome')
    autocomplete_fields = ['fabricante', 'fornecedor']
    readonly_fields = ('filial',)
    fieldsets = (
        (None, {
            'fields': (
                'filial', 'nome', 'modelo', 'fabricante', 'fornecedor',
                'certificado_aprovacao', 'data_validade_ca', 'vida_util_dias',
                'estoque_minimo', 'requer_numero_serie', 'foto', 'observacoes', 'ativo'
            )
        }),
    )

    # ============================================================ #
    # == CORREÇÃO ADICIONADA AQUI TAMBÉM ==
    # Mesma lógica aplicada ao EquipamentoAdmin para consistência.
    # ============================================================ #
    def save_model(self, request, obj, form, change):
        if not obj.filial_id: # Apenas se a filial não estiver definida
             active_filial = getattr(request.user, 'filial_ativa', None)
             if active_filial:
                 obj.filial = active_filial
        super().save_model(request, obj, form, change)


# FichaEPIAdmin já estava correto.
@admin.register(FichaEPI)
class FichaEPIAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    inlines = [EntregaEPIInline]
    list_display = ('funcionario', 'filial', 'get_funcao_display', 'atualizado_em')
    list_select_related = ('funcionario', 'funcionario__cargo', 'funcionario__funcao', 'filial')
    search_fields = ('funcionario__nome_completo', 'funcionario__matricula')
    autocomplete_fields = ['funcionario']
    readonly_fields = ('filial', 'data_admissao', 'get_funcao_display', 'criado_em', 'atualizado_em')
    list_filter = ('funcionario__cargo', 'filial') # Adicionado filial
    
    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if obj.funcionario:
            obj.filial = obj.funcionario.filial
        super().save_model(request, obj, form, change)

    @admin.display(description=_('Cargo'), ordering='funcionario__cargo__nome')
    def get_funcionario_cargo(self, obj):
        return obj.funcionario.cargo.nome if obj.funcionario and obj.funcionario.cargo else "N/A"
    
    @admin.display(description=_('Função (SST)'), ordering='funcionario__funcao__nome')
    def get_funcao_display(self, obj):
        if obj.funcao:
            return obj.funcao.nome
        return "---"

@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('data', 'filial', 'equipamento', 'tipo', 'quantidade', 'responsavel')
    list_filter = ('tipo', 'equipamento', 'responsavel', 'filial') # Adicionado filial
    search_fields = ('equipamento__nome', 'responsavel__username', 'justificativa')
    autocomplete_fields = ['equipamento', 'responsavel', 'fornecedor', 'entrega_associada']
    readonly_fields = ('filial', 'data',)