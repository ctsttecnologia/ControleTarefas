# departamento_pessoal/admin.py

from django.contrib import admin
from .models import Departamento, Cargo, Funcionario, Documento
from core.mixins import FilialAdminScopedMixin 

# --- Inlines para a Visão de Funcionário ---

class DocumentoInline(admin.TabularInline):
    model = Documento
    extra = 1
    fields = ('tipo', 'numero', 'anexo')


# --- Configurações dos Admins Principais ---

@admin.register(Departamento)
class DepartamentoAdmin(FilialAdminScopedMixin, admin.ModelAdmin):
    list_display = ('nome', 'filial', 'ativo')
    search_fields = ('nome',)
    list_filter = ('ativo',) # O filtro por filial é menos necessário agora
    readonly_fields = ('filial',) # Impede a edição da filial após a criação

@admin.register(Cargo)
class CargoAdmin(FilialAdminScopedMixin, admin.ModelAdmin):
    list_display = ('nome', 'filial', 'cbo', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'cbo')
    list_editable = ('ativo',) # REATORADO: Removido 'filial' para segurança
    readonly_fields = ('filial',) # Impede a edição da filial após a criação

@admin.register(Funcionario)
class FuncionarioAdmin(FilialAdminScopedMixin, admin.ModelAdmin):
    inlines = [DocumentoInline]
    
    list_display = ('nome_completo', 'filial', 'matricula', 'cargo', 'departamento', 'status')
    list_filter = ('status', 'departamento', 'cargo')
    search_fields = ('nome_completo', 'matricula', 'usuario__username', 'usuario__email')
    
    list_select_related = ('usuario', 'cargo', 'departamento', 'filial')
    autocomplete_fields = ['usuario', 'cargo', 'departamento']
    
    fieldsets = (
        ('Vínculo com o Sistema', {
            'fields': ('usuario',)
        }),
        ('Vínculo Organizacional', { # REATORADO: Adicionado 'filial' como readonly
            'fields': ('filial', 'matricula', 'departamento', 'cargo', 'data_admissao', 'status', 'data_demissao')
        }),
        ('Informações Pessoais', {
            'fields': ('nome_completo', 'data_nascimento', 'idade', 'sexo', 'email_pessoal', 'telefone')
        }),
        ('Dados de Remuneração', {
            'fields': ('salario',)
        }),
    )
    readonly_fields = ('idade', 'filial') # Impede a edição da filial após a criação