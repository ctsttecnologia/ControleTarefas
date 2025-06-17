
from django.contrib import admin
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
    actions_on_top = True
    actions_on_bottom = True

# Departamento
@admin.register(Departamentos)
class DepartamentosAdmin(BaseAdmin):
    list_display = ('nome', 'sigla', 'tipo', 'centro_custo', 'ativo', 'data_criacao')
    list_filter = ('tipo', 'ativo')
    search_fields = ('nome', 'sigla', 'centro_custo')
    list_editable = ('ativo',)
    readonly_fields = ('data_criacao', 'data_atualizacao')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'sigla', 'tipo')
        }),
        ('Dados Financeiros', {
            'fields': ('centro_custo',)
        }),
        ('Status e Datas', {
            'fields': ('ativo', 'data_criacao', 'data_atualizacao')
        }),
    )

# CBOs
@admin.register(Cbos)
class CbosAdmin(BaseAdmin):
    list_display = ('codigo', 'titulo', 'data_atualizacao')
    search_fields = ('codigo', 'titulo', 'descricao')
    readonly_fields = ('data_atualizacao',)
    
    fieldsets = (
        ('Dados do CBO', {
            'fields': ('codigo', 'titulo', 'descricao')
        }),
        ('Metadados', {
            'fields': ('data_atualizacao',)
        }),
    )

# Cargos
@admin.register(Cargos)
class CargosAdmin(BaseAdmin):
    list_display = ('nome', 'cbo', 'salario_base', 'ativo')
    list_filter = ('ativo', 'cbo')
    search_fields = ('nome', 'descricao')
    list_editable = ('ativo', 'salario_base')
    raw_id_fields = ('cbo',)
    
    fieldsets = (
        ('Informações do Cargo', {
            'fields': ('nome', 'cbo', 'descricao')
        }),
        ('Remuneração', {
            'fields': ('salario_base',)
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
    )

# Documentos - Inline para Funcionarios
class DocumentosInline(admin.TabularInline):
    model = Documentos
    extra = 1  # Mostra 1 formulário vazio por padrão
    min_num = 0  # Permite zero documentos
    fields = ('nome', 'sigla', 'tipo', 'cpf', 'rg', 'data_criacao', 'ativo', 'download_anexos')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'download_anexos')
    show_change_link = True
    
    def download_anexos(self, obj):
        if obj.anexo_cpf or obj.anexo_ctps or obj.anexo_pis or obj.anexo_rg:
            links = []
            if obj.anexo_cpf:
                links.append(f'<a href="{obj.anexo_cpf.url}" target="_blank">CPF</a>')
            if obj.anexo_ctps:
                links.append(f'<a href="{obj.anexo_ctps.url}" target="_blank">CTPS</a>')
            if obj.anexo_pis:
                links.append(f'<a href="{obj.anexo_pis.url}" target="_blank">PIS</a>')
            if obj.anexo_rg:
                links.append(f'<a href="{obj.anexo_rg.url}" target="_blank">RG</a>')
            return format_html(' | '.join(links))
        return "-"
    download_anexos.short_description = "Anexos"

# Admissão - Inline para Funcionarios
class AdmissaoInline(admin.StackedInline):
    model = Admissao
    extra = 0
    fieldsets = (
        (None, {
            'fields': ('matricula', 'cargo', 'departamento', 'tipo_contrato')
        }),
        ('Datas', {
            'fields': ('data_admissao', 'data_demissao')
        }),
        ('Remuneração', {
            'fields': ('salario',)
        }),
        ('Horário', {
            'fields': ('hora_entrada', 'hora_saida', 'dias_semana')
        }),
        ('Documentação', {
            'fields': ('documento_principal',)
        }),
    )
    readonly_fields = ('tempo_empresa',)
    show_change_link = True
    
    def funcionario_display(self, obj):
        return obj.funcionario.nome if obj.funcionario else "N/D"
    funcionario_display.short_description = 'Funcionário'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('funcionario', 'cargo', 'departamento')

# Funcionarios
@admin.register(Funcionarios)
class FuncionariosAdmin(BaseAdmin):
    list_display = ('nome', 'email', 'sexo', 'estatus', 'idade', 'matricula_display', 'telefone_formatado', 'total_documentos')
    list_filter = ('sexo', 'estatus', 'data_cadastro')
    search_fields = ('nome', 'email', 'telefone')
    readonly_fields = ('data_cadastro', 'idade', 'telefone_formatado', 'total_documentos')
    inlines = [AdmissaoInline, DocumentosInline]
    
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('nome', 'data_nascimento', 'idade', 'sexo', 'naturalidade')
        }),
        ('Contato', {
            'fields': ('email', 'telefone', 'telefone_formatado', 'logradouro')
        }),
        ('Documentos', {
            'fields': ('total_documentos',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('estatus', 'data_cadastro')
        }),
    )
    
    def total_documentos(self, obj):
        return obj.documentos.count()
    total_documentos.short_description = 'Total de Documentos'
    
    def matricula_display(self, obj):
        # Acessa a matrícula através do relacionamento inverso
        return obj.admissao.matricula if hasattr(obj, 'admissao') else "N/D"
    matricula_display.short_description = 'Matrícula'
    
    def telefone_formatado(self, obj):
        return obj.telefone_formatado
    telefone_formatado.short_description = 'Telefone'

# Admissao
@admin.register(Admissao)
class AdmissaoAdmin(BaseAdmin):
    list_display = ('matricula', 'funcionario', 'cargo', 'departamento', 'data_admissao', 'tipo_contrato', 'salario', 'tempo_empresa')
    list_filter = ('tipo_contrato', 'departamento', 'cargo', 'data_admissao')
    search_fields = ('matricula', 'funcionario__nome', 'cargo__nome', 'departamento__nome')
    readonly_fields = ('tempo_empresa',)
    raw_id_fields = ('funcionario', 'cargo', 'departamento', 'documento_principal')
    
    fieldsets = (
        ('Informações Principais', {
            'fields': ('funcionario', 'matricula', 'cargo', 'departamento', 'tipo_contrato')
        }),
        ('Datas', {
            'fields': ('data_admissao', 'data_demissao', 'tempo_empresa')
        }),
        ('Remuneração', {
            'fields': ('salario',)
        }),
        ('Horário de Trabalho', {
            'fields': ('hora_entrada', 'hora_saida', 'dias_semana')
        }),
        ('Documentação', {
            'fields': ('documento_principal',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('funcionario', 'cargo', 'departamento')

# Documentos
@admin.register(Documentos)
class DocumentosAdmin(BaseAdmin):
    list_display = ('funcionario_link', 'nome', 'tipo', 'cpf', 'rg', 'ativo', 'data_criacao', 'download_links')
    list_filter = ('tipo', 'ativo', 'data_criacao')
    search_fields = ('funcionario__nome', 'nome', 'cpf', 'pis', 'rg')
    list_editable = ('ativo',)
    readonly_fields = ('data_atualizacao', 'download_links')
    raw_id_fields = ('funcionario',)
    
    fieldsets = (
        ('Identificação', {
            'fields': ('funcionario', 'nome', 'sigla', 'tipo', 'centro_custo')
        }),
        ('Documentos Pessoais', {
            'fields': ('cpf', 'pis', 'ctps', 'rg', 'emissor', 'uf', 'reservista', 'titulo_eleitor')
        }),
        ('Anexos', {
            'fields': ('anexo_cpf', 'anexo_ctps', 'anexo_pis', 'anexo_rg', 'download_links')
        }),
        ('Status', {
            'fields': ('ativo', 'data_criacao', 'data_atualizacao')
        }),
    )
    
    def funcionario_link(self, obj):
        url = reverse("admin:departamento_pessoal_funcionarios_change", args=[obj.funcionario.id])
        return format_html('<a href="{}">{}</a>', url, obj.funcionario.nome)
    funcionario_link.short_description = 'Funcionário'
    funcionario_link.admin_order_field = 'funcionario__nome'
    
    def download_links(self, obj):
        links = []
        if obj.anexo_cpf:
            links.append(f'<a href="{obj.anexo_cpf.url}" target="_blank">CPF</a>')
        if obj.anexo_ctps:
            links.append(f'<a href="{obj.anexo_ctps.url}" target="_blank">CTPS</a>')
        if obj.anexo_pis:
            links.append(f'<a href="{obj.anexo_pis.url}" target="_blank">PIS</a>')
        if obj.anexo_rg:
            links.append(f'<a href="{obj.anexo_rg.url}" target="_blank">RG</a>')
        return format_html(' | '.join(links)) if links else "-"
    download_links.short_description = "Download Anexos"

