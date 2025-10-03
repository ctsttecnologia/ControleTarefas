
# seguranca_trabalho/admin.py

from django.contrib import admin
from django.contrib.admin import TabularInline
from django.utils.translation import gettext_lazy as _

from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin
# Modelos que ainda existem nesta aplicação
from .models import (
    Funcao, Equipamento, MatrizEPI, FichaEPI, EntregaEPI, MovimentacaoEstoque
)


# =============================================================================
# CLASSES INLINE
# Usadas para editar modelos relacionados dentro de outros modelos.
# =============================================================================

class MatrizEPIInline(TabularInline):
    model = MatrizEPI
    extra = 1
    autocomplete_fields = ['equipamento']
    readonly_fields = ('filial',)

    # Lógica para filtrar equipamentos pela filial da função (objeto pai)
    def get_formset(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "equipamento" and hasattr(request, '_obj_') and request._obj_ and request._obj_.filial:
            kwargs["queryset"] = Equipamento.objects.filter(filial=request._obj_.filial)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class EntregaEPIInline(TabularInline):
    model = EntregaEPI
    extra = 1
    autocomplete_fields = ['equipamento']
    readonly_fields = ('filial', 'criado_em',)

    # Lógica para filtrar equipamentos pela filial da ficha (objeto pai)
    def get_formset(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "equipamento" and hasattr(request, '_obj_') and request._obj_ and request._obj_.filial:
            kwargs["queryset"] = Equipamento.objects.filter(filial=request._obj_.filial)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =============================================================================
# CLASSES ADMIN PRINCIPAIS
# =============================================================================

@admin.register(Funcao)
class FuncaoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'filial', 'ativo')
    list_filter = ('ativo', 'filial')
    search_fields = ('nome',)
    readonly_fields = ('filial',)
    inlines = [MatrizEPIInline]

    # Passa o objeto para o request para ser usado pelo inline
    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

    # Define a filial automaticamente com base no usuário logado, se não definida
    def save_model(self, request, obj, form, change):
        if not obj.filial_id:
            active_filial = getattr(request.user, 'filial_ativa', None)
            if active_filial:
                obj.filial = active_filial
        super().save_model(request, obj, form, change)


@admin.register(Equipamento)
class EquipamentoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'modelo', 'fabricante', 'data_validade_ca', 'ativo', 'filial')
    list_filter = ('ativo', 'filial', 'fabricante', 'requer_numero_serie')
    search_fields = ('nome', 'modelo', 'certificado_aprovacao', 'fabricante__nome_fantasia')
    autocomplete_fields = ['fabricante']  # REMOVIDO: 'fornecedor' não existe mais neste modelo
    list_select_related = ('fabricante', 'filial')  # REMOVIDO: 'fornecedor'
    readonly_fields = ('filial',)
    fieldsets = (
        (None, {
            'fields': (
                'filial', 'nome', 'modelo', 'fabricante',  # REMOVIDO: 'fornecedor'
                'certificado_aprovacao', 'data_validade_ca', 'vida_util_dias',
                'estoque_minimo', 'requer_numero_serie', 'foto', 'observacoes', 'ativo'
            )
        }),
    )

    # Define a filial automaticamente com base no usuário logado, se não definida
    def save_model(self, request, obj, form, change):
        if not obj.filial_id:
            active_filial = getattr(request.user, 'filial_ativa', None)
            if active_filial:
                obj.filial = active_filial
        super().save_model(request, obj, form, change)


@admin.register(FichaEPI)
class FichaEPIAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('funcionario', 'get_funcao_display', 'atualizado_em', 'filial')
    list_filter = ('funcionario__cargo', 'filial')
    search_fields = ('funcionario__nome_completo', 'funcionario__matricula')
    autocomplete_fields = ['funcionario']
    list_select_related = ('funcionario', 'funcionario__cargo', 'funcionario__funcao', 'filial')
    readonly_fields = ('filial', 'data_admissao', 'get_funcao_display', 'criado_em', 'atualizado_em')
    inlines = [EntregaEPIInline]

    # Passa o objeto para o request para ser usado pelo inline
    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

    # Define a filial com base na filial do funcionário associado
    def save_model(self, request, obj, form, change):
        if obj.funcionario:
            obj.filial = obj.funcionario.filial
        super().save_model(request, obj, form, change)

    @admin.display(description=_('Função (SST)'), ordering='funcionario__funcao__nome')
    def get_funcao_display(self, obj):
        return obj.funcao.nome if obj.funcao else "---"


@admin.register(EntregaEPI)
class EntregaEPIAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('ficha', 'equipamento', 'data_entrega', 'status', 'filial')
    list_filter = ('equipamento', 'data_entrega', 'data_devolucao', 'filial')
    search_fields = ('equipamento__nome', 'ficha__funcionario__nome_completo')
    autocomplete_fields = ['ficha', 'equipamento']
    readonly_fields = ('filial', 'criado_em',)

    # Define a filial com base na filial da ficha de EPI associada
    def save_model(self, request, obj, form, change):
        if obj.ficha:
            obj.filial = obj.ficha.filial
        super().save_model(request, obj, form, change)


@admin.register(MatrizEPI)
class MatrizEPIAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('funcao', 'equipamento', 'frequencia_troca_meses', 'filial')
    list_filter = ('filial', 'funcao', 'equipamento')
    search_fields = ('funcao__nome', 'equipamento__nome')
    autocomplete_fields = ['funcao', 'equipamento']
    list_select_related = ('funcao', 'equipamento', 'filial')

    # Define a filial com base na filial da função associada
    def save_model(self, request, obj, form, change):
        if obj.funcao:
            obj.filial = obj.funcao.filial
        super().save_model(request, obj, form, change)


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('data', 'equipamento', 'tipo', 'quantidade', 'responsavel', 'filial')
    list_filter = ('tipo', 'equipamento', 'responsavel', 'filial')
    search_fields = ('equipamento__nome', 'responsavel__username', 'justificativa')
    autocomplete_fields = ['equipamento', 'responsavel', 'fornecedor', 'entrega_associada']
    readonly_fields = ('filial', 'data',)

   
