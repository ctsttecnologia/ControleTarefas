
# departamento_pessoal/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    Departamentos, 
    Cbos, 
    Cargos, 
    Funcionarios, 
    Documentos, 
    Admissao
)

# Configurações comuns
class BaseAdmin(admin.ModelAdmin):
    list_per_page = 25
    save_on_top = True

# --- Admins Auxiliares (Departamentos, Cbos, Cargos) ---
# Estes estavam corretos e não precisaram de grandes mudanças.
@admin.register(Departamentos)
class DepartamentosAdmin(BaseAdmin):
    list_display = ('nome', 'sigla', 'tipo', 'centro_custo', 'ativo', 'data_criacao')
    list_filter = ('tipo', 'ativo')
    search_fields = ('nome', 'sigla', 'centro_custo')
    list_editable = ('ativo',)

@admin.register(Cbos)
class CbosAdmin(BaseAdmin):
    list_display = ('codigo', 'titulo')
    search_fields = ('codigo', 'titulo')

@admin.register(Cargos)
class CargosAdmin(BaseAdmin):
    list_display = ('nome', 'cbo', 'salario_base', 'ativo')
    list_filter = ('ativo', 'cbo')
    search_fields = ('nome',)
    list_editable = ('ativo', 'salario_base')
    raw_id_fields = ('cbo',)

# --- Inlines para a View de Funcionário ---

class DocumentosInline(admin.TabularInline):
    model = Documentos
    extra = 1
    min_num = 0
    # CORREÇÃO: Atualizado para refletir os novos campos do modelo Documentos.
    fields = ('tipo', 'cpf', 'rg', 'ctps', 'anexo', 'download_anexo')
    readonly_fields = ('download_anexo',)
    show_change_link = True

    # OTIMIZAÇÃO: Método simplificado para lidar com um único campo 'anexo'.
    def download_anexo(self, obj):
        if obj.anexo:
            return format_html('<a href="{}" target="_blank">Baixar</a>', obj.anexo.url)
        return "Sem anexo"
    download_anexo.short_description = "Anexo"

class AdmissaoInline(admin.StackedInline):
    model = Admissao
    extra = 0
    # CORREÇÃO: Removido o fieldset 'Documentação' e o campo 'documento_principal', que não existem mais.
    fieldsets = (
        (None, {'fields': ('matricula', 'cargo', 'departamento', 'tipo_contrato')}),
        ('Datas', {'fields': ('data_admissao', 'data_demissao')}),
        ('Remuneração', {'fields': ('salario',)}),
        ('Horário', {'fields': ('hora_entrada', 'hora_saida', 'dias_semana')}),
    )
    raw_id_fields = ('cargo', 'departamento')
    show_change_link = True

# --- Admin Principal de Funcionários ---
@admin.register(Funcionarios)
class FuncionariosAdmin(BaseAdmin):
    list_display = ('nome', 'email', 'estatus', 'matricula_display', 'telefone_formatado')
    list_filter = ('estatus', 'sexo', 'admissao__departamento', 'admissao__cargo')
    search_fields = ('nome', 'email', 'admissao__matricula')
    readonly_fields = ('idade', 'telefone_formatado')
    inlines = [AdmissaoInline, DocumentosInline]
    
    fieldsets = (
        ('Informações Pessoais', {'fields': ('nome', 'data_nascimento', 'idade', 'sexo', 'naturalidade')}),
        ('Contato', {'fields': ('email', 'telefone', 'telefone_formatado', 'logradouro')}),
        ('Status', {'fields': ('estatus',)}),
    )

    def matricula_display(self, obj):
        try:
            return obj.admissao.matricula
        except Admissao.DoesNotExist:
            return "N/D"
    matricula_display.short_description = 'Matrícula'
    matricula_display.admin_order_field = 'admissao__matricula'

    def get_queryset(self, request):
        # OTIMIZAÇÃO: `select_related` para otimizar a busca da matrícula e do telefone formatado.
        return super().get_queryset(request).select_related('admissao')

# --- Admins Independentes (Admissao e Documentos) ---
@admin.register(Admissao)
class AdmissaoAdmin(BaseAdmin):
    list_display = ('matricula', 'get_funcionario_link', 'cargo', 'departamento', 'data_admissao', 'tipo_contrato')
    list_filter = ('tipo_contrato', 'departamento', 'cargo', 'data_admissao')
    search_fields = ('matricula', 'funcionario__nome', 'cargo__nome', 'departamento__nome')
    # CORREÇÃO: Removido 'documento_principal' que não existe mais.
    raw_id_fields = ('funcionario', 'cargo', 'departamento')

    def get_funcionario_link(self, obj):
        url = reverse("admin:departamento_pessoal_funcionarios_change", args=[obj.funcionario.id])
        return format_html('<a href="{}">{}</a>', url, obj.funcionario.nome)
    get_funcionario_link.short_description = 'Funcionário'
    get_funcionario_link.admin_order_field = 'funcionario__nome'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('funcionario', 'cargo', 'departamento')


@admin.register(Documentos)
class DocumentosAdmin(BaseAdmin):
    list_display = ('get_funcionario_link', 'tipo', 'cpf', 'rg', 'download_anexo')
    list_filter = ('tipo',)
    search_fields = ('funcionario__nome', 'cpf', 'pis', 'rg')
    raw_id_fields = ('funcionario',)
    
    # CORREÇÃO: Fieldsets completamente refeitos para corresponder ao novo modelo.
    fieldsets = (
        ('Identificação', {'fields': ('funcionario', 'tipo')}),
        ('Dados do Documento', {'fields': ('cpf', 'pis', 'ctps', 'rg', 'uf_emissor_rg', 'orgao_emissor_rg', 'reservista', 'titulo_eleitor')}),
        ('Anexo', {'fields': ('anexo', 'download_anexo')}),
    )
    readonly_fields = ('download_anexo',)

    def get_funcionario_link(self, obj):
        url = reverse("admin:departamento_pessoal_funcionarios_change", args=[obj.funcionario.id])
        return format_html('<a href="{}">{}</a>', url, obj.funcionario.nome)
    get_funcionario_link.short_description = 'Funcionário'
    get_funcionario_link.admin_order_field = 'funcionario__nome'

    # OTIMIZAÇÃO: Reutilizando o mesmo método do inline.
    def download_anexo(self, obj):
        if obj.anexo:
            return format_html('<a href="{}" target="_blank">Baixar Arquivo</a>', obj.anexo.url)
        return "Nenhum arquivo enviado"
    download_anexo.short_description = 'Download'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('funcionario')

