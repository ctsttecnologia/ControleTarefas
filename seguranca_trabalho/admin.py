from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Equipamento, MatrizEPI, FichaEPI, EntregaEPI,
    MovimentacaoEstoque, Funcao, Fabricante, Fornecedor
)

# --- Inlines ---
# ... (Seus Inlines continuam iguais) ...
class MatrizEPIInline(admin.TabularInline):
    model = MatrizEPI
    extra = 1
    autocomplete_fields = ['equipamento']

class EntregaEPIInline(admin.TabularInline): # <<-- ÁREA DA CORREÇÃO
    model = EntregaEPI
    extra = 0
    fields = ('equipamento', 'quantidade', 'lote', 'numero_serie', 'data_entrega', 'status', 'validade')
    # O campo 'status' funciona pois é uma @property no modelo EntregaEPI.
    # O campo 'validade' precisa ser definido aqui no inline.
    readonly_fields = ('status', 'validade')
    autocomplete_fields = ['equipamento']
    
    # --- MÉTODO ADICIONADO AQUI ---
    @admin.display(description='Validade do Uso')
    def validade(self, obj):
        """Calcula e exibe a data de vencimento do uso do EPI."""
        if obj and obj.pk and obj.data_vencimento_uso:
            return obj.data_vencimento_uso.strftime("%d/%m/%Y")
        return '—'

# --- Registros dos Novos Modelos ---
@admin.register(Fabricante)
class FabricanteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'ativo')
    search_fields = ('nome', 'cnpj')
    list_editable = ('ativo',)

@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('nome_fantasia', 'razao_social', 'cnpj', 'email', 'telefone', 'ativo')
    search_fields = ('nome_fantasia', 'razao_social', 'cnpj')
    list_editable = ('ativo',)

@admin.register(Funcao)
class FuncaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao_resumida', 'ativo')
    search_fields = ('nome', 'descricao')
    list_editable = ('ativo',)
    list_filter = ('ativo',)
    inlines = [MatrizEPIInline]

    @admin.display(description='Descrição')
    def descricao_resumida(self, obj):
        if obj.descricao and len(obj.descricao) > 100:
            return obj.descricao[:100] + '...'
        return obj.descricao or '—'
    
@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'modelo', 'fabricante', 'certificado_aprovacao', 'data_validade_ca', 'ativo', 'requer_numero_serie')
    list_filter = ('ativo', 'requer_numero_serie', 'fabricante', 'fornecedor_padrao')
    search_fields = ('nome', 'modelo', 'certificado_aprovacao', 'fabricante__nome')
    list_editable = ('ativo', 'requer_numero_serie')
    autocomplete_fields = ['fabricante', 'fornecedor_padrao']
    
    fieldsets = (
        ("Informações Principais", {
            'fields': ('nome', 'modelo', 'fabricante', 'foto', 'ativo')
        }),
        ("Certificação e Validade", {
            'fields': ('certificado_aprovacao', 'data_validade_ca', 'vida_util_dias')
        }),
        ("Gestão e Compra", {
            'fields': ('fornecedor_padrao', 'estoque_minimo', 'requer_numero_serie')
        }),
        ("Detalhes Adicionais", {
            'fields': ('observacoes',)
        }),
    )

@admin.register(FichaEPI)
class FichaEPIAdmin(admin.ModelAdmin):
    inlines = [EntregaEPIInline]
    list_display = ('colaborador', 'funcao', 'data_admissao', 'total_epis', 'atualizado_em')
    list_filter = ('funcao', 'data_admissao')
    search_fields = ('colaborador__first_name', 'colaborador__last_name', 'colaborador__username')
    autocomplete_fields = ['colaborador', 'funcao']
    date_hierarchy = 'data_admissao'

    @admin.display(description='Total de Entregas')
    def total_epis(self, obj):
        return obj.entregas.count()

@admin.register(EntregaEPI)
class EntregaEPIAdmin(admin.ModelAdmin):
    list_display = ('ficha_colaborador', 'equipamento', 'quantidade', 'lote', 'numero_serie', 'data_entrega', 'status')
    search_fields = ('ficha__colaborador__first_name', 'equipamento__nome', 'lote', 'numero_serie')
    autocomplete_fields = ['ficha', 'equipamento']
    date_hierarchy = 'data_entrega'
    list_select_related = ('ficha__colaborador', 'equipamento')

    @admin.display(description='Colaborador', ordering='ficha__colaborador__first_name')
    def ficha_colaborador(self, obj):
        return obj.ficha.colaborador.get_full_name()

@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('data', 'equipamento', 'tipo', 'quantidade', 'lote', 'fornecedor', 'custo_unitario', 'responsavel')
    list_filter = ('tipo', 'data', 'equipamento', 'fornecedor')
    search_fields = ('equipamento__nome', 'lote', 'justificativa', 'fornecedor__nome_fantasia')
    autocomplete_fields = ['equipamento', 'responsavel', 'fornecedor']
    date_hierarchy = 'data'
    list_select_related = ('equipamento', 'responsavel', 'fornecedor')

