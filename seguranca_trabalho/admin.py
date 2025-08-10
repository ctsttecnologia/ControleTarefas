# seguranca_trabalho/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Fabricante, Fornecedor, Funcao, Equipamento,
    MatrizEPI, FichaEPI, EntregaEPI, MovimentacaoEstoque
)
from core.admin import FilialAdminMixin

# =============================================================================
# ADMIN ACTIONS
# =============================================================================

@admin.action(description=_('Marcar equipamentos selecionados como inativos'))
def marcar_como_inativo(modeladmin, request, queryset):
    """Ação para desativar múltiplos equipamentos de uma vez."""
    queryset.update(ativo=False)

# =============================================================================
# INLINE ADMINS
# Utilizados para editar modelos relacionados dentro da página de outro modelo.
# =============================================================================

class MatrizEPIInline(admin.TabularInline):
    """Permite adicionar/editar a Matriz de EPIs diretamente na página de uma Função."""
    model = MatrizEPI
    extra = 1  # Mostra um formulário extra para adição.
    autocomplete_fields = ['equipamento']
    verbose_name = _("EPI requerido para esta função")
    verbose_name_plural = _("EPIs requeridos para esta função")


class EntregaEPIInline(admin.TabularInline):
    """Permite visualizar as entregas de EPI diretamente na Ficha do funcionário."""
    model = EntregaEPI
    extra = 0  # Não mostra formulários extras por padrão.
    fields = ('equipamento', 'quantidade', 'data_entrega', 'status_da_entrega', 'data_devolucao')
    readonly_fields = ('status_da_entrega',)
    autocomplete_fields = ['equipamento']
    ordering = ('-criado_em',)

    @admin.display(description=_('Status'))
    def status_da_entrega(self, obj):
        # Reutiliza a propriedade 'status' do modelo EntregaEPI
        if obj.pk:
            return obj.status
        return _("Nova Entrega")

# =============================================================================
# MODEL ADMINS
# Define a aparência e o comportamento dos modelos na interface de administração.
# =============================================================================

@admin.register(Fabricante)
class FabricanteAdmin(FilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'filial','cnpj', 'ativo')
    list_filter = ('ativo', 'filial')
    search_fields = ('nome', 'cnpj')
    list_per_page = 20


@admin.register(Fornecedor)
class FornecedorAdmin(FilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome_fantasia', 'filial', 'razao_social', 'cnpj', 'ativo')
    list_filter = ('ativo', 'filial')
    search_fields = ('nome_fantasia', 'razao_social', 'cnpj')
    list_per_page = 20


@admin.register(Funcao)
class FuncaoAdmin(FilialAdminMixin, admin.ModelAdmin):
    inlines = [MatrizEPIInline]
    list_display = ('nome', 'filial', 'ativo')
    list_filter = ('ativo', 'filial')
    search_fields = ('nome',)


@admin.register(Equipamento)
class EquipamentoAdmin(FilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'filial', 'modelo', 'fabricante', 'certificado_aprovacao', 'data_validade_ca', 'ativo')
    list_filter = ('ativo', 'filial', 'fabricante', 'requer_numero_serie')
    search_fields = ('nome', 'modelo', 'certificado_aprovacao', 'fabricante__nome')
    autocomplete_fields = ['fabricante', 'fornecedor_padrao']
    actions = [marcar_como_inativo]
    list_per_page = 25

    fieldsets = (
        (_('Identificação do Equipamento'), {
            'fields': ('nome', 'modelo', 'foto', 'fabricante', 'fornecedor_padrao')
        }),
        (_('Validade e Certificação (CA)'), {
            'fields': ('certificado_aprovacao', 'data_validade_ca', 'vida_util_dias')
        }),
        (_('Controle Interno'), {
            'fields': ('estoque_minimo', 'requer_numero_serie', 'ativo', 'observacoes')
        }),
    )


@admin.register(FichaEPI)
class FichaEPIAdmin(FilialAdminMixin, admin.ModelAdmin):
    inlines = [EntregaEPIInline]
    list_display = ('funcionario', 'filial', 'get_funcionario_cargo', 'data_admissao', 'atualizado_em')
    list_select_related = ('funcionario', 'funcionario__cargo') # Otimiza a busca
    search_fields = ('funcionario__nome_completo', 'funcionario__id')
    autocomplete_fields = ['funcionario']
    readonly_fields = ('data_admissao', 'funcao', 'criado_em', 'atualizado_em')
    list_per_page = 20
    
    fieldsets = (
        (None, {
            'fields': ('funcionario',)
        }),
        (_('Dados da Ficha (preenchido automaticamente)'), {
            'classes': ('collapse',), # Começa recolhido
            'fields': ('funcao', 'data_admissao', 'criado_em', 'atualizado_em'),
        }),
    )

    @admin.display(description=_('Cargo do Funcionário'), ordering='funcionario__cargo__nome')
    def get_funcionario_cargo(self, obj):
        if obj.funcionario and obj.funcionario.cargo:
            return obj.funcionario.cargo.nome
        return _("Não informado")


@admin.register(EntregaEPI)
class EntregaEPIAdmin(FilialAdminMixin, admin.ModelAdmin):
    list_display = ('ficha', 'filial', 'equipamento', 'data_entrega', 'status_da_entrega', 'data_devolucao')
    list_filter = ('equipamento', 'filial', 'data_entrega', 'data_devolucao')
    search_fields = ('equipamento__nome', 'ficha__funcionario__nome_completo')
    autocomplete_fields = ['ficha', 'equipamento']
    date_hierarchy = 'criado_em'
    readonly_fields = ('criado_em',)
    list_per_page = 30

    fieldsets = (
        (_('Informações da Entrega'), {
            'fields': ('ficha', 'equipamento', 'quantidade')
        }),
        (_('Rastreabilidade (Opcional)'), {
            'fields': ('lote', 'numero_serie')
        }),
        (_('Status e Assinatura'), {
            'fields': ('data_entrega', 'data_devolucao', 'assinatura_recebimento', 'criado_em')
        }),
    )

    @admin.display(description=_('Status'))
    def status_da_entrega(self, obj):
        return obj.status


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(FilialAdminMixin, admin.ModelAdmin):
    list_display = ('data', 'filial', 'equipamento', 'tipo', 'quantidade', 'responsavel', 'justificativa')
    list_filter = ('tipo', 'filial', 'equipamento', 'responsavel')
    search_fields = ('equipamento__nome', 'responsavel__username', 'justificativa', 'lote')
    autocomplete_fields = ['equipamento', 'responsavel', 'fornecedor', 'entrega_associada']
    readonly_fields = ('data',)
    date_hierarchy = 'data'
    list_per_page = 30
