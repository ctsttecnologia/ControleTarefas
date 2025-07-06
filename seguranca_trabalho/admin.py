# seguranca_trabalho/admin.py

from django.contrib import admin
from .models import (
    Fabricante, Fornecedor, Funcao, Equipamento, 
    MatrizEPI, FichaEPI, EntregaEPI, MovimentacaoEstoque
)

# --- INLINES ---
# (Estes são usados dentro de outros admins)

class MatrizEPIInline(admin.TabularInline):
    model = MatrizEPI
    extra = 1
    autocomplete_fields = ['equipamento']

class EntregaEPIInline(admin.TabularInline):
    model = EntregaEPI
    extra = 0
    fields = ('equipamento', 'quantidade', 'data_entrega', 'display_status')
    readonly_fields = ('display_status',)
    autocomplete_fields = ['equipamento']

    @admin.display(description='Status')
    def display_status(self, obj):
        if obj.pk:  # Garante que o objeto já foi salvo
            return obj.status
        return "Novo"

# --- ADMINS PRINCIPAIS ---

@admin.register(Fabricante)
class FabricanteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo')
    search_fields = ('nome',)

@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('nome_fantasia', 'razao_social', 'ativo')
    search_fields = ('nome_fantasia', 'razao_social', 'cnpj')

@admin.register(Funcao)
class FuncaoAdmin(admin.ModelAdmin):
    inlines = [MatrizEPIInline]
    list_display = ('nome', 'ativo')
    search_fields = ('nome',)

# CORREÇÃO 1: Registrando o EquipamentoAdmin
@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'modelo', 'fabricante', 'certificado_aprovacao', 'ativo')
    list_filter = ('ativo', 'fabricante')
    # search_fields é o que permite que o autocomplete funcione em outras classes
    search_fields = ('nome', 'modelo', 'certificado_aprovacao')
    autocomplete_fields = ['fabricante']

@admin.register(FichaEPI)
class FichaEPIAdmin(admin.ModelAdmin):
    inlines = [EntregaEPIInline]
    list_display = ('__str__', 'funcionario_cargo', 'atualizado_em')
    search_fields = ('funcionario__nome_completo', 'funcionario__matricula')
    autocomplete_fields = ['funcionario']
    list_select_related = ('funcionario__cargo',)

    @admin.display(description='Cargo do Funcionário', ordering='funcionario__cargo__nome')
    def funcionario_cargo(self, obj):
        return obj.funcionario.cargo

# CORREÇÃO 2: Registrando o EntregaEPIAdmin e corrigindo o 'status'
@admin.register(EntregaEPI)
class EntregaEPIAdmin(admin.ModelAdmin):
    # Usando o método 'display_status' em vez do campo direto
    list_display = ('__str__', 'data_entrega', 'display_status')
    search_fields = ('equipamento__nome', 'ficha__funcionario__nome_completo')
    autocomplete_fields = ['ficha', 'equipamento']

    @admin.display(description='Status', ordering='data_devolucao')
    def display_status(self, obj):
        # Reutiliza a lógica da propriedade do modelo
        return obj.status

@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('data', 'equipamento', 'tipo', 'quantidade', 'responsavel')
    list_filter = ('tipo', 'equipamento')
    autocomplete_fields = ['equipamento', 'responsavel', 'fornecedor', 'entrega_associada']