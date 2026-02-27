
from datetime import timezone
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from usuario.models import Filial
from .models import (
    Empresa, LocalPrestacaoServico, ProfissionalResponsavel, AmbienteTrabalho,
    PGRDocumento, PGRDocumentoResponsavel, PGRRevisao,
    GESGrupoExposicao,
    TipoRisco, RiscoIdentificado, AvaliacaoQuantitativa, MedidaControle, RiscoMedidaControle,
    PlanoAcaoPGR, AcompanhamentoPlanoAcao,
    CronogramaAcaoPGR,
    RiscoEPIRecomendado, RiscoTreinamentoNecessario
)

# Ação customizada para o Admin
@admin.action(description='Marcar planos de ação selecionados como Concluídos')
def marcar_como_concluido(modeladmin, request, queryset):
    queryset.update(status='concluido', data_conclusao=timezone.now().date())

# ===========================================
# Base Admin para Filtro de Filial
# ===========================================

class BasePGRAdmin(admin.ModelAdmin):
    """Admin base para filtrar automaticamente por filial e preencher criado_por."""
    exclude = ('criado_por',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'filial'):
            return qs.filter(filial=request.user.filial)
        # Retorna queryset vazio se o usuário não for superuser e não tiver filial
        return qs.none() 

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and hasattr(request.user, 'filial'):
            if 'filial' in db_field.name:
                kwargs['queryset'] = Filial.objects.filter(id=request.user.filial.id)
                kwargs['initial'] = request.user.filial.id
                kwargs['disabled'] = True
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    

# ===========================================
# Inlines
# ===========================================

# Agora, crie a classe para o formulário "inline"
class PGRDocumentoResponsavelInline(admin.TabularInline):
    model = PGRDocumentoResponsavel
    extra = 1  # Mostra 1 formulário em branco por padrão
    # Este campo de busca é essencial para encontrar profissionais facilmente
    autocomplete_fields = ['profissional'] 

class PGRDocumentoResponsavelInline(admin.TabularInline):
    model = PGRDocumentoResponsavel
    extra = 1
    verbose_name = "Profissional Responsável"
    verbose_name_plural = "Profissionais Responsáveis"
    autocomplete_fields = ['profissional']

class PGRRevisaoInline(admin.TabularInline):
    model = PGRRevisao
    extra = 1
    ordering = ('-numero_revisao',)

class CronogramaAcaoPGRInline(admin.TabularInline):
    model = CronogramaAcaoPGR
    extra = 1
    ordering = ('numero_item',)

class AvaliacaoQuantitativaInline(admin.TabularInline):
    model = AvaliacaoQuantitativa
    extra = 1
    fields = ('tipo_avaliacao', 'data_avaliacao', 'resultado_medido', 'unidade_medida', 'conforme')

class RiscoMedidaControleInline(admin.TabularInline):
    model = RiscoMedidaControle
    extra = 1

class RiscoEPIRecomendadoInline(admin.TabularInline):
    model = RiscoEPIRecomendado
    extra = 1

class RiscoTreinamentoNecessarioInline(admin.TabularInline):
    model = RiscoTreinamentoNecessario
    extra = 1

class AcompanhamentoPlanoAcaoInline(admin.TabularInline):
    model = AcompanhamentoPlanoAcao
    extra = 1
    readonly_fields = ('criado_em', 'criado_por')
    fields = ('data_acompanhamento', 'status_atual', 'percentual_conclusao', 'descricao', 'responsavel_acompanhamento')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Preenche automaticamente o usuário que está logado
        if db_field.name == "criado_por":
            kwargs['initial'] = request.user.id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ===========================================
# ModelAdmins
# ===========================================

# Primeiro, garanta que o Django saiba como buscar profissionais
@admin.register(ProfissionalResponsavel)
class ProfissionalResponsavelAdmin(admin.ModelAdmin):
    search_fields = ['nome_completo', 'registro_classe']
    list_display = ('nome_completo', 'funcao', 'registro_classe')
    list_filter = ('funcao',)


# Finalmente, modifique a administração do PGRDocumento para usar o inline
@admin.register(PGRDocumento)
class PGRDocumentoAdmin(admin.ModelAdmin):
    list_display = ('codigo_documento', 'empresa', 'status', 'data_vencimento')
    search_fields = ('codigo_documento', 'empresa__nome_fantasia')
    # Adicione outras configurações que você já tenha (list_filter, etc.)
    
    # Esta é a linha mais importante: ela adiciona o formulário de responsáveis
    inlines = [PGRDocumentoResponsavelInline]


@admin.register(Empresa)
class EmpresaAdmin(BasePGRAdmin):
    list_display = ('razao_social', 'cnpj', 'grau_risco', 'tipo_empresa', 'filial', 'ativo')
    list_filter = ('tipo_empresa', 'grau_risco', 'filial', 'ativo')
    search_fields = ('cliente__razao_social', 'cnpj')
    fieldsets = (
        ('Informações Principais', {
            'fields': ('filial', 'cliente', 'cnpj', 'tipo_empresa')
        }),
        ('Classificação e Dados Ocupacionais', {
            'fields': ('cnae_especifico', 'descricao_cnae', 'atividade_principal', 'grau_risco', 'grau_risco_texto', 'numero_empregados', 'numero_empregados_texto', 'jornada_trabalho')
        }),
        ('Endereço e Contato', {
            'classes': ('collapse',),
            'fields': ('endereco', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'cep', 'telefone', 'email')
        }),
    )

@admin.register(LocalPrestacaoServico)
class LocalPrestacaoServicoAdmin(BasePGRAdmin):
    list_display = ('razao_social', 'empresa', 'cidade', 'estado', 'filial', 'ativo')
    list_filter = ('empresa', 'estado', 'filial')
    search_fields = ('razao_social', 'cnpj', 'empresa__razao_social')

@admin.register(AmbienteTrabalho)
class AmbienteTrabalhoAdmin(BasePGRAdmin):
    list_display = ('codigo', 'nome', 'empresa', 'local_prestacao', 'filial')
    search_fields = ('codigo', 'nome', 'empresa__razao_social')
    list_filter = ('empresa', 'filial')


@admin.register(GESGrupoExposicao)
class GESGrupoExposicaoAdmin(BasePGRAdmin):
    list_display = ('codigo', 'nome', 'pgr_documento', 'cargo', 'funcao', 'numero_trabalhadores', 'total_riscos', 'riscos_criticos')
    list_filter = ('pgr_documento__empresa', 'cargo', 'funcao', 'filial')
    search_fields = ('codigo', 'nome', 'pgr_documento__codigo_documento', 'descricao_atividades')
    autocomplete_fields = ['pgr_documento', 'ambiente_trabalho', 'cargo', 'funcao']

@admin.register(TipoRisco)
class TipoRiscoAdmin(BasePGRAdmin):
    list_display = ('nome', 'categoria', 'display_cor', 'nr_referencia')
    list_filter = ('categoria',)
    search_fields = ('nome', 'descricao')

    @admin.display(description='Cor')
    def display_cor(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px;">{}</span>',
            obj.codigo_cor, obj.codigo_cor
        )

@admin.register(RiscoIdentificado)
class RiscoIdentificadoAdmin(BasePGRAdmin):
    list_display = ('agente', 'tipo_risco', 'pgr_documento_link', 'ges', 'display_classificacao', 'prioridade_acao', 'status_controle')
    list_filter = ('classificacao_risco', 'prioridade_acao', 'status_controle', 'tipo_risco__categoria', 'pgr_documento__empresa', 'filial')
    search_fields = ('agente', 'fonte_geradora', 'ges__nome', 'pgr_documento__codigo_documento')
    autocomplete_fields = ['pgr_documento', 'ges', 'ambiente_trabalho', 'cargo', 'tipo_risco', ]
    readonly_fields = ('severidade_s', 'classificacao_risco', 'prioridade_acao', 'criado_em', 'atualizado_em', 'criado_por')
    inlines = [AvaliacaoQuantitativaInline, RiscoMedidaControleInline, RiscoEPIRecomendadoInline, RiscoTreinamentoNecessarioInline]
    
    fieldsets = (
        ('Vinculação', {'fields': ('filial', 'pgr_documento', 'ges', 'ambiente_trabalho', 'cargo')}),
        ('Identificação do Risco', {'fields': ('tipo_risco', 'agente', 'fonte_geradora', 'meio_propagacao', 'perfil_exposicao', 'possiveis_efeitos_saude', 'data_identificacao')}),
        ('Avaliação de Risco (Matriz)', {'fields': (('gravidade_g', 'exposicao_e'), ('probabilidade_p', 'severidade_s'), ('classificacao_risco', 'prioridade_acao'))}),
        ('Controle e Observações', {'fields': ('status_controle', 'metodo_avaliacao', 'medidas_controle_existentes', 'observacoes')}),
        ('Autoria', {'classes': ('collapse',), 'fields': ('criado_por', 'criado_em', 'atualizado_em')}),
    )

    @admin.display(description='Classificação', ordering='classificacao_risco')
    def display_classificacao(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 5px;">{}</span>',
            obj.cor_classificacao, obj.get_classificacao_risco_display()
        )
    
    @admin.display(description='Documento PGR')
    def pgr_documento_link(self, obj):
        if obj.pgr_documento:
            url = reverse('admin:pgr_gestao_pgrdocumento_change', args=[obj.pgr_documento.id])
            return format_html('<a href="{}">{}</a>', url, obj.pgr_documento.codigo_documento)
        return "-"

@admin.register(MedidaControle)
class MedidaControleAdmin(BasePGRAdmin):
    list_display = ('descricao', 'tipo_controle', 'prioridade', 'nr_referencia', 'filial')
    list_filter = ('tipo_controle', 'prioridade', 'filial')
    search_fields = ('descricao',)

@admin.register(PlanoAcaoPGR)
class PlanoAcaoPGRAdmin(BasePGRAdmin):
    list_display = ('descricao_acao', 'risco_identificado', 'status', 'prioridade', 'data_prevista', 'responsavel', 'display_atrasado')
    list_filter = ('status', 'prioridade', 'tipo_acao', 'data_prevista', 'filial')
    search_fields = ('descricao_acao', 'responsavel', 'risco_identificado__agente')
    autocomplete_fields = ['risco_identificado']
    readonly_fields = ('criado_em', 'atualizado_em', 'criado_por', 'esta_atrasado', 'dias_atraso')
    inlines = [AcompanhamentoPlanoAcaoInline]
    actions = [marcar_como_concluido]
    
    fieldsets = (
        ('Ação de Controle', {'fields': ('filial', 'risco_identificado', 'tipo_acao', 'descricao_acao', 'justificativa', 'recursos_necessarios')}),
        ('Prazos e Responsabilidades', {'fields': ('prioridade', 'status', 'responsavel', 'data_prevista', 'data_conclusao')}),
        ('Custos', {'classes': ('collapse',), 'fields': (('custo_estimado', 'custo_real'),)}),
        ('Resultados e Evidências', {'classes': ('collapse',), 'fields': ('resultado_obtido', 'eficacia_acao', 'evidencia_conclusao', 'evidencia')}),
        ('Autoria', {'classes': ('collapse',), 'fields': ('criado_por', 'criado_em', 'atualizado_em')}),
    )

    @admin.display(description='Atrasado?', boolean=True, ordering='data_prevista')
    def display_atrasado(self, obj):
        return obj.esta_atrasado

# Registro dos modelos que não precisam de uma classe Admin complexa
# A maioria já é gerenciada via inlines, mas tê-los registrados permite fácil acesso.
admin.site.register(PGRRevisao)
admin.site.register(CronogramaAcaoPGR)
admin.site.register(AvaliacaoQuantitativa)
admin.site.register(AcompanhamentoPlanoAcao)
