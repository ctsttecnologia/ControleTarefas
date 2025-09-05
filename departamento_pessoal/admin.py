# departamento_pessoal/admin.py

from django.contrib import admin
from .models import Departamento, Cargo, Funcionario, Documento
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin

# --- Inlines para a Visão de Funcionário ---

class DocumentoInline(admin.TabularInline):
    model = Documento
    extra = 1
    # O campo 'filial' é removido. Ele deve ser herdado do Funcionário.
    # A lógica para isso deve ficar no método save() do modelo Documento.
    fields = ('tipo', 'numero', 'anexo')
    
# --- Configurações dos Admins Principais ---

@admin.register(Departamento)
class DepartamentoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    # O mixin FilialAdminScopedMixin já filtra por filial.
    list_display = ('nome', 'filial', 'ativo')
    search_fields = ('nome',)
    list_filter = ('ativo',) # Filtro por filial é redundante agora
    # Impede a edição da filial após a criação.
    readonly_fields = ('filial',)

@admin.register(Cargo)
class CargoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    # O mixin FilialAdminScopedMixin já filtra por filial.
    list_display = ('nome', 'filial', 'cbo', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'cbo')
    # Impede a edição da filial após a criação.
    readonly_fields = ('filial',)

@admin.register(Funcionario)
class FuncionarioAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    inlines = [DocumentoInline]
    
    list_display = ('nome_completo', 'filial', 'matricula', 'cargo', 'departamento', 'status')
    # O mixin já filtra por filial, então o filtro explícito é opcional.
    # Pode ser mantido se um superuser sem filial selecionada quiser filtrar manualmente.
    list_filter = ('status', 'departamento', 'cargo', 'filial') 
    search_fields = ('nome_completo', 'matricula', 'usuario__username', 'usuario__email')
    
    list_select_related = ('usuario', 'cargo', 'departamento', 'filial')
    autocomplete_fields = ['usuario', 'cargo', 'departamento']
    
    fieldsets = (
        ('Vínculo com o Sistema', {
            'fields': ('usuario',)
        }),
        # REATORADO: 'filial' adicionado aqui como readonly
        ('Vínculo Organizacional', {
            'fields': ('filial', 'matricula', 'departamento', 'cargo', 'data_admissao', 'status', 'data_demissao')
        }),
        ('Informações Pessoais', {
            'fields': ('nome_completo', 'data_nascimento', 'idade', 'sexo', 'email_pessoal', 'telefone')
        }),
        ('Dados de Remuneração', {
            'fields': ('salario',)
        }),
    )
    # REATORADO: 'filial' é agora readonly para garantir a integridade dos dados.
    readonly_fields = ('idade', 'filial')

    