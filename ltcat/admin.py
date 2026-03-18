
# ltcat/admin.py

from django.contrib import admin
from .models import (
    EmpresaLTCAT, LocalPrestacaoServicoLTCAT, ProfissionalResponsavelLTCAT,
    LTCATDocumento, LTCATDocumentoResponsavel, RevisaoLTCAT,
    LTCATSecaoTexto, LTCATSecaoTextoPadrao,
    FuncaoAnalisada, ReconhecimentoRisco,
    AvaliacaoPericulosidade, ConclusaoFuncao,
    RecomendacaoTecnica, AnexoLTCAT, TabelaRuidoNR15,
    DocumentoLocalPrestacao,
)


# =============================================================================
# EMPRESA E LOCAIS
# =============================================================================

@admin.register(EmpresaLTCAT)
class EmpresaLTCATAdmin(admin.ModelAdmin):
    list_display = ['razao_social', 'cnpj', 'cidade', 'estado', 'filial', 'ativo']
    search_fields = ['cliente__razao_social', 'cnpj']
    list_filter = ['filial', 'ativo', 'estado']
    raw_id_fields = ['cliente']


@admin.register(LocalPrestacaoServicoLTCAT)
class LocalPrestacaoServicoLTCATAdmin(admin.ModelAdmin):
    list_display = ['nome_local', 'razao_social', 'cidade_display', 'empresa', 'filial']
    search_fields = ['nome_local', 'razao_social', 'cnpj', 'cidade']
    list_filter = ['estado', 'filial', 'empresa']
    autocomplete_fields = ['logradouro', 'empresa']


@admin.register(ProfissionalResponsavelLTCAT)
class ProfissionalResponsavelAdmin(admin.ModelAdmin):
    list_display = ['nome_completo', 'funcao', 'registro_classe', 'orgao_classe', 'filial']
    search_fields = ['nome_completo', 'registro_classe']
    list_filter = ['filial']
    raw_id_fields = ['funcionario']


# =============================================================================
# DOCUMENTO LTCAT — INLINES
# (Todos os inlines ANTES do Admin que os usa)
# =============================================================================

class ResponsavelInline(admin.TabularInline):
    model = LTCATDocumentoResponsavel
    extra = 0


class RevisaoInline(admin.TabularInline):
    model = RevisaoLTCAT
    extra = 0
    fields = ['numero_revisao', 'descricao', 'data_realizada', 'realizada_por']


class SecaoTextoInline(admin.StackedInline):
    model = LTCATSecaoTexto
    extra = 0
    fields = ['secao', 'titulo_customizado', 'conteudo', 'ordem', 'incluir_no_pdf']


class FuncaoInline(admin.TabularInline):
    model = FuncaoAnalisada
    extra = 0
    show_change_link = True
    fields = ['nome_funcao', 'cbo', 'ghe', 'departamento', 'ativo']


class PericulosidadeInline(admin.TabularInline):
    model = AvaliacaoPericulosidade
    extra = 0
    fields = ['tipo', 'aplicavel', 'descricao']


class ConclusaoInline(admin.TabularInline):
    model = ConclusaoFuncao
    extra = 0
    fields = [
        'funcao', 'tipo_conclusao', 'codigo_gfip',
        'faz_jus_insalubridade', 'faz_jus_periculosidade',
        'faz_jus_aposentadoria_especial'
    ]


class RecomendacaoInline(admin.TabularInline):
    model = RecomendacaoTecnica
    extra = 0
    fields = ['descricao', 'prioridade', 'implementada', 'ordem']


class AnexoInline(admin.TabularInline):
    model = AnexoLTCAT
    extra = 0
    fields = ['tipo', 'numero_romano', 'titulo', 'arquivo', 'ordem', 'incluir_no_pdf']


class DocumentoLocalPrestacaoInline(admin.TabularInline):
    model = DocumentoLocalPrestacao
    extra = 1
    autocomplete_fields = ['local_prestacao']
    fields = ['local_prestacao', 'principal', 'ordem', 'observacoes']


# =============================================================================
# DOCUMENTO LTCAT
# =============================================================================

@admin.register(LTCATDocumento)
class LTCATDocumentoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo_documento', 'empresa', 'filial',
        'data_elaboracao', 'status', 'versao_atual', 'ativo'
    ]
    list_filter = ['status', 'filial', 'data_elaboracao', 'ativo']
    search_fields = ['codigo_documento', 'empresa__razao_social', 'titulo']
    readonly_fields = ['criado_em', 'atualizado_em', 'criado_por']
    date_hierarchy = 'data_elaboracao'
    autocomplete_fields = ['empresa', 'empresa_contratada']
    inlines = [
        DocumentoLocalPrestacaoInline, ResponsavelInline, RevisaoInline,
        SecaoTextoInline, FuncaoInline, PericulosidadeInline,
        ConclusaoInline, RecomendacaoInline, AnexoInline,
    ]

    fieldsets = (
        ('Identificação', {
            'fields': (
                'codigo_documento', 'titulo',
                'filial', 'status', 'versao_atual'
            )
        }),
        ('Empresas', {
            'fields': ('empresa', 'empresa_contratada'),
            'description': 'Contratante = Cliente | Contratada = CETEST'
        }),
        ('Datas', {
            'fields': ('data_elaboracao', 'data_ultima_revisao', 'data_vencimento')
        }),
        ('Conteúdo Resumido', {
            'classes': ('collapse',),
            'fields': (
                'objetivo', 'condicoes_preliminares',
                'avaliacao_periculosidade_texto',
                'referencias_bibliograficas', 'observacoes'
            )
        }),
        ('Auditoria', {
            'classes': ('collapse',),
            'fields': ('criado_por', 'criado_em', 'atualizado_em', 'ativo')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)


# =============================================================================
# FUNÇÃO E RISCOS
# =============================================================================

class RiscoInline(admin.TabularInline):
    model = ReconhecimentoRisco
    extra = 0
    fields = [
        'tipo_risco', 'agente', 'fonte_geradora',
        'tipo_avaliacao', 'limite_tolerancia',
        'resultado_avaliacao', 'exposicao'
    ]


@admin.register(FuncaoAnalisada)
class FuncaoAnalisadaAdmin(admin.ModelAdmin):
    list_display = ['nome_funcao', 'cbo', 'ghe', 'departamento', 'ltcat_documento', 'ativo']
    search_fields = ['nome_funcao', 'cbo', 'ghe']
    list_filter = ['ltcat_documento__filial', 'ativo']
    raw_id_fields = ['ltcat_documento', 'local_prestacao', 'cargo', 'funcao_st']
    inlines = [RiscoInline]


@admin.register(ReconhecimentoRisco)
class ReconhecimentoRiscoAdmin(admin.ModelAdmin):
    list_display = [
        'agente', 'tipo_risco', 'fonte_geradora',
        'tipo_avaliacao', 'resultado_avaliacao', 'exposicao', 'funcao'
    ]
    list_filter = ['tipo_risco', 'tipo_avaliacao', 'exposicao']
    search_fields = ['agente', 'fonte_geradora']
    raw_id_fields = ['funcao']


# =============================================================================
# PERICULOSIDADE, CONCLUSÕES, RECOMENDAÇÕES
# =============================================================================

@admin.register(AvaliacaoPericulosidade)
class AvaliacaoPericulosidadeAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'aplicavel', 'ltcat_documento']
    list_filter = ['aplicavel', 'tipo']
    raw_id_fields = ['ltcat_documento']


@admin.register(ConclusaoFuncao)
class ConclusaoFuncaoAdmin(admin.ModelAdmin):
    list_display = [
        'funcao', 'tipo_conclusao', 'codigo_gfip',
        'faz_jus_insalubridade', 'faz_jus_periculosidade',
        'faz_jus_aposentadoria_especial'
    ]
    list_filter = ['tipo_conclusao', 'codigo_gfip', 'faz_jus_insalubridade']
    raw_id_fields = ['ltcat_documento', 'funcao']


@admin.register(RecomendacaoTecnica)
class RecomendacaoTecnicaAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'prioridade', 'implementada', 'ltcat_documento']
    list_filter = ['prioridade', 'implementada']
    raw_id_fields = ['ltcat_documento']


# =============================================================================
# ANEXOS
# =============================================================================

@admin.register(AnexoLTCAT)
class AnexoLTCATAdmin(admin.ModelAdmin):
    list_display = ['titulo_completo', 'tipo', 'ltcat_documento', 'extensao', 'tamanho_formatado', 'criado_em']
    list_filter = ['tipo', 'incluir_no_pdf']
    search_fields = ['titulo', 'descricao']
    raw_id_fields = ['ltcat_documento']
    readonly_fields = ['nome_arquivo_original', 'tamanho_arquivo', 'criado_em', 'atualizado_em']


# =============================================================================
# SEÇÕES DE TEXTO
# =============================================================================

@admin.register(LTCATSecaoTexto)
class LTCATSecaoTextoAdmin(admin.ModelAdmin):
    list_display = ['secao', 'ltcat_documento', 'ordem', 'incluir_no_pdf']
    list_filter = ['secao', 'incluir_no_pdf']
    raw_id_fields = ['ltcat_documento']


@admin.register(LTCATSecaoTextoPadrao)
class LTCATSecaoTextoPadraoAdmin(admin.ModelAdmin):
    list_display = ['secao', 'titulo', 'ativo']
    list_filter = ['ativo']
    search_fields = ['titulo', 'conteudo_padrao']


# =============================================================================
# TABELA DE REFERÊNCIA NR-15
# =============================================================================

@admin.register(TabelaRuidoNR15)
class TabelaRuidoNR15Admin(admin.ModelAdmin):
    list_display = ['nivel_ruido_db', 'max_exposicao_diaria']
    ordering = ['nivel_ruido_db']
