
# departamento_pessoal/admin.py

from django.contrib import admin
from .models import Departamento, Cargo, Funcionario, Documento

# --- Inlines para a Visão de Funcionário ---

class DocumentoInline(admin.TabularInline):
    """Permite adicionar/editar Documentos na mesma tela de Funcionário."""
    model = Documento
    extra = 1  # Quantos formulários em branco exibir
    fields = ('tipo', 'numero', 'anexo')


# --- Configurações dos Admins Principais ---

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo')
    search_fields = ('nome',)
    list_editable = ('ativo',)

@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cbo', 'ativo')
    search_fields = ('nome', 'cbo')
    list_editable = ('ativo',)

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    inlines = [DocumentoInline]  # <-- Inclui o formulário de documentos aqui
    
    list_display = ('nome_completo', 'matricula', 'cargo', 'departamento', 'status', 'idade')
    list_filter = ('status', 'departamento', 'cargo')
    search_fields = ('nome_completo', 'matricula', 'usuario__username', 'usuario__email')
    
    # Otimiza a busca, carregando os dados relacionados de uma só vez
    list_select_related = ('usuario', 'cargo', 'departamento')
    
    # Melhora a experiência de selecionar ForeignKeys com muitos itens
    autocomplete_fields = ['usuario', 'cargo', 'departamento']
    
    # Organiza o formulário de edição em seções lógicas
    fieldsets = (
        ('Vinculo com o Sistema', {
            'fields': ('usuario',)
        }),
        ('Informações Pessoais', {
            'fields': ('nome_completo', 'data_nascimento', 'idade', 'sexo', 'email_pessoal', 'telefone')
        }),
        ('Dados de Contratação', {
            'fields': ('matricula', 'departamento', 'cargo', 'data_admissao', 'salario', 'status', 'data_demissao')
        }),
    )
    # Campos que são calculados e não devem ser editáveis
    readonly_fields = ('idade',)
