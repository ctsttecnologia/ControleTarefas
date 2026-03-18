
# departamento_pessoal/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Departamento, Cargo, Funcionario, Documento
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin


# ─────────────────────────────────────────────
# Inlines
# ─────────────────────────────────────────────

class DocumentoInline(admin.TabularInline):
    """
    Inline simplificado para documentos no admin do Funcionário.
    Filial é herdada automaticamente do Funcionário no save().
    """
    model = Documento
    extra = 0
    show_change_link = True
    fields = ('tipo_documento', 'numero', 'data_emissao', 'data_validade', 'anexo')
    exclude = ('filial',)


# ─────────────────────────────────────────────
# Departamento
# ─────────────────────────────────────────────

@admin.register(Departamento)
class DepartamentoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('registro', 'nome', 'filial', 'ativo')
    search_fields = ('nome',)
    list_filter = ('ativo',)
    readonly_fields = ('filial',)


# ─────────────────────────────────────────────
# Cargo
# ─────────────────────────────────────────────

@admin.register(Cargo)
class CargoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'filial', 'cbo', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'cbo')
    readonly_fields = ('filial',)


# ─────────────────────────────────────────────
# Funcionário
# ─────────────────────────────────────────────

@admin.register(Funcionario)
class FuncionarioAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    inlines = [DocumentoInline]

    list_display = (
        'nome_completo', 'filial', 'matricula', 'cargo',
        'funcao', 'departamento', 'status',
    )
    list_filter = ('status', 'departamento', 'cargo', 'funcao', 'filial')
    search_fields = ('nome_completo', 'matricula', 'usuario__username', 'usuario__email')
    list_select_related = ('usuario', 'cargo', 'departamento', 'filial')
    autocomplete_fields = ['usuario', 'cargo', 'departamento']

    fieldsets = (
        ('Vínculo com o Sistema', {
            'fields': ('usuario',)
        }),
        ('Vínculo Organizacional', {
            'fields': (
                'filial', 'matricula', 'departamento', 'cargo',
                'funcao', 'data_admissao', 'status', 'data_demissao',
            )
        }),
        ('Informações Pessoais', {
            'fields': (
                'nome_completo', 'data_nascimento', 'idade',
                'sexo', 'email_pessoal', 'telefone',
            )
        }),
        ('Dados de Remuneração', {
            'fields': ('salario',)
        }),
    )
    readonly_fields = ('idade', 'filial')


# ─────────────────────────────────────────────
# Documento (admin dedicado)
# ─────────────────────────────────────────────

@admin.register(Documento)
class DocumentoAdmin(AdminFilialScopedMixin, admin.ModelAdmin):
    """Admin completo para gerenciar documentos individualmente."""

    list_display = (
        'funcionario', 'tipo_documento', 'numero',
        'data_emissao', 'data_validade', 'status_validade',
        'tem_anexo',
    )
    list_filter = ('tipo_documento', 'filial', 'uf_expedidor')
    search_fields = (
        'funcionario__nome_completo', 'numero',
        'orgao_expedidor', 'outro_descricao',
    )
    list_select_related = ('funcionario', 'filial')
    list_per_page = 30
    date_hierarchy = 'criado_em'

    fieldsets = (
        ('Dados Principais', {
            'fields': (
                'funcionario', 'tipo_documento', 'numero',
                'data_emissao', 'data_validade',
                'orgao_expedidor', 'uf_expedidor',
            ),
        }),
        ('RG', {
            'classes': ('collapse',),
            'description': 'Preencha apenas se o tipo for RG.',
            'fields': ('rg_nome_pai', 'rg_nome_mae', 'rg_naturalidade'),
        }),
        ('CNH', {
            'classes': ('collapse',),
            'description': 'Preencha apenas se o tipo for CNH.',
            'fields': (
                'cnh_categoria', 'cnh_numero_registro',
                'cnh_primeira_habilitacao', 'cnh_observacoes_detran',
            ),
        }),
        ('CTPS', {
            'classes': ('collapse',),
            'description': 'Preencha apenas se o tipo for CTPS.',
            'fields': ('ctps_serie', 'ctps_uf', 'ctps_digital'),
        }),
        ('Título de Eleitor', {
            'classes': ('collapse',),
            'fields': ('titulo_zona', 'titulo_secao', 'titulo_municipio'),
        }),
        ('Reservista', {
            'classes': ('collapse',),
            'fields': ('reservista_categoria', 'reservista_regiao_militar'),
        }),
        ('Registro de Classe', {
            'classes': ('collapse',),
            'fields': ('registro_orgao', 'registro_especialidade'),
        }),
        ('ASO - Atestado de Saúde Ocupacional', {
            'classes': ('collapse',),
            'fields': (
                'aso_tipo_exame', 'aso_apto',
                'aso_medico_nome', 'aso_medico_crm',
                'aso_proximo_exame',
            ),
        }),
        ('Certificado NR', {
            'classes': ('collapse',),
            'fields': ('nr_numero', 'nr_carga_horaria', 'nr_instituicao'),
        }),
        ('Certificado / Diploma', {
            'classes': ('collapse',),
            'fields': (
                'certificado_nivel', 'certificado_curso',
                'certificado_instituicao',
            ),
        }),
        ('Passaporte', {
            'classes': ('collapse',),
            'fields': ('passaporte_pais_emissao',),
        }),
        ('Outro', {
            'classes': ('collapse',),
            'fields': ('outro_descricao',),
        }),
        ('Anexo e Observações', {
            'fields': ('anexo', 'observacoes'),
        }),
        ('Controle', {
            'classes': ('collapse',),
            'fields': ('filial',),
        }),
    )

    @admin.display(description='Status', ordering='data_validade')
    def status_validade(self, obj):
        if not obj.data_validade:
            return '-'
        if obj.esta_vencido:
            return format_html(
                '<span style="color:#dc3545;font-weight:600;">⚠ Vencido</span>'
            )
        if obj.vence_em_30_dias:
            return format_html(
                '<span style="color:#ffc107;font-weight:600;">⏳ Vence em breve</span>'
            )
        return format_html(
            '<span style="color:#198754;font-weight:600;">✅ Válido</span>'
        )

    @admin.display(description='Anexo', boolean=True)
    def tem_anexo(self, obj):
        return bool(obj.anexo)

    def save_model(self, request, obj, form, change):
        """Herda a filial do funcionário automaticamente."""
        if not obj.filial_id and obj.funcionario_id:
            obj.filial = obj.funcionario.filial
        super().save_model(request, obj, form, change)
