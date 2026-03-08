
# treinamentos/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum

from .models import (
    # Models originais
    TipoCurso, Treinamento, Participante, GabaritoCertificado, Assinatura,
    # Models EAD
    CursoEAD, ModuloEAD, AulaEAD, PlanoEstudo, PlanoEstudoCurso,
    MatriculaEAD, ProgressoAulaEAD, AvaliacaoEAD, QuestaoEAD,
    AlternativaEAD, TentativaAvaliacaoEAD, RespostaAlunoEAD, CertificadoEAD,
)


# =============================================================================
# MODELS ORIGINAIS
# =============================================================================

@admin.register(TipoCurso)
class TipoCursoAdmin(admin.ModelAdmin):
    list_display = ("nome", "modalidade", "area", "validade_meses", "ativo")
    list_filter = ("ativo", "modalidade", "area")
    search_fields = ("nome",)


class ParticipanteInline(admin.TabularInline):
    model = Participante
    extra = 0
    autocomplete_fields = ("funcionario",)


@admin.register(Treinamento)
class TreinamentoAdmin(admin.ModelAdmin):
    list_display = (
        "nome", "tipo_curso", "palestrante", "data_inicio",
        "data_fim", "status", "filial",
    )
    list_filter = ("status", "tipo_curso", "filial", "data_inicio")
    search_fields = ("nome", "tipo_curso__nome", "palestrante")
    date_hierarchy = "data_inicio"
    inlines = [ParticipanteInline]


@admin.register(Participante)
class ParticipanteAdmin(admin.ModelAdmin):
    list_display = ("funcionario", "treinamento", "presente", "nota_avaliacao")
    list_filter = ("presente", "treinamento__tipo_curso")
    search_fields = (
        "funcionario__first_name", "funcionario__last_name",
        "treinamento__nome",
    )
    autocomplete_fields = ("funcionario", "treinamento")


@admin.register(GabaritoCertificado)
class GabaritoCertificadoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_filter = ("ativo",)


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ("__str__", "nome_assinante", "data_assinatura", "esta_assinada")
    list_filter = ("data_assinatura",)
    search_fields = ("nome_assinante", "documento_assinante")

    @admin.display(description="Assinada?", boolean=True)
    def esta_assinada(self, obj):
        return obj.esta_assinada


# =============================================================================
# =============================================================================
#
#  EAD — ADMIN COMPLETO
#
# =============================================================================
# =============================================================================


# --------------- Inlines para CursoEAD ---------------

class ModuloEADInline(admin.TabularInline):
    model = ModuloEAD
    extra = 0
    fields = ("ordem", "titulo", "descricao", "ativo", "link_aulas")
    readonly_fields = ("link_aulas",)
    ordering = ("ordem",)
    show_change_link = True

    def link_aulas(self, obj):
        if not obj.pk:
            return "—"
        url = (
            reverse("admin:treinamentos_aulaead_changelist")
            + f"?modulo__id__exact={obj.pk}"
        )
        count = obj.aulas_ead.count()
        return format_html('<a href="{}">{} aula(s)</a>', url, count)
    link_aulas.short_description = "Aulas"


class AvaliacaoEADInlineForCurso(admin.StackedInline):
    model = AvaliacaoEAD
    extra = 0
    fields = (
        "titulo", "descricao", "tempo_limite_min",
        "embaralhar_questoes", "embaralhar_alternativas", "ativo",
    )
    show_change_link = True


# --------------- CursoEAD ---------------

@admin.register(CursoEAD)
class CursoEADAdmin(admin.ModelAdmin):
    list_display = (
        "titulo", "tipo_curso", "nivel", "carga_horaria_total",
        "qtd_modulos", "qtd_aulas", "status",
        "destaque", "filial", "criado_em",
    )
    list_filter = ("status", "destaque", "nivel", "tipo_curso", "filial")
    search_fields = ("titulo", "slug", "descricao")
    prepopulated_fields = {"slug": ("titulo",)}
    autocomplete_fields = ("tipo_curso", "criado_por", "filial")
    readonly_fields = ("criado_em", "atualizado_em", "publicado_em")
    list_editable = ("status", "destaque")
    date_hierarchy = "criado_em"
    inlines = [ModuloEADInline, AvaliacaoEADInlineForCurso]

    fieldsets = (
        ("Informações do Curso", {
            "fields": (
                "titulo", "slug", "descricao", "descricao_curta",
                "imagem_capa", "tipo_curso", "nivel", "carga_horaria_total",
            ),
        }),
        ("Instrutor", {
            "fields": ("instrutor_nome", "instrutor_qualificacao"),
        }),
        ("Configurações Pedagógicas", {
            "fields": (
                "nota_minima", "max_tentativas_avaliacao",
                "percentual_minimo_assistido",
            ),
        }),
        ("Publicação", {
            "fields": ("status", "destaque", "publicado_em"),
        }),
        ("Vínculo", {
            "fields": ("filial", "criado_por"),
        }),
        ("Datas", {
            "classes": ("collapse",),
            "fields": ("criado_em", "atualizado_em"),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _total_modulos=Count("modulos_ead", distinct=True),
            _total_aulas=Count("modulos_ead__aulas_ead", distinct=True),
        )

    @admin.display(description="Módulos", ordering="_total_modulos")
    def qtd_modulos(self, obj):
        return obj._total_modulos

    @admin.display(description="Aulas", ordering="_total_aulas")
    def qtd_aulas(self, obj):
        return obj._total_aulas


# --------------- ModuloEAD ---------------

class AulaEADInline(admin.TabularInline):
    model = AulaEAD
    extra = 0
    fields = (
        "ordem", "titulo", "tipo_conteudo",
        "duracao_estimada_min", "obrigatoria", "ativo",
    )
    ordering = ("ordem",)
    show_change_link = True


@admin.register(ModuloEAD)
class ModuloEADAdmin(admin.ModelAdmin):
    list_display = ("__str__", "curso", "ordem", "ativo", "qtd_aulas")
    list_filter = ("curso", "ativo")
    search_fields = ("titulo", "curso__titulo")
    autocomplete_fields = ("curso",)
    inlines = [AulaEADInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_total_aulas=Count("aulas_ead"))

    @admin.display(description="Aulas", ordering="_total_aulas")
    def qtd_aulas(self, obj):
        return obj._total_aulas


# --------------- AulaEAD ---------------

@admin.register(AulaEAD)
class AulaEADAdmin(admin.ModelAdmin):
    list_display = (
        "__str__", "modulo", "tipo_conteudo",
        "duracao_estimada_min", "obrigatoria", "ativo",
    )
    list_filter = ("tipo_conteudo", "obrigatoria", "ativo", "modulo__curso")
    search_fields = ("titulo", "modulo__titulo", "modulo__curso__titulo")
    autocomplete_fields = ("modulo",)
    readonly_fields = ("embed_url_preview", "criado_em")

    fieldsets = (
        ("Identificação", {
            "fields": ("modulo", "titulo", "ordem", "descricao"),
        }),
        ("Conteúdo", {
            "fields": (
                "tipo_conteudo", "arquivo_video", "url_video_externo",
                "embed_url_preview", "arquivo_pdf", "conteudo_texto",
            ),
        }),
        ("Configuração", {
            "fields": ("duracao_estimada_min", "obrigatoria", "ativo", "criado_em"),
        }),
    )

    def embed_url_preview(self, obj):
        url = obj.embed_url
        if url:
            return format_html(
                '<iframe width="420" height="236" src="{}" '
                'frameborder="0" allowfullscreen></iframe><br>'
                '<code>{}</code>',
                url, url,
            )
        return "—"
    embed_url_preview.short_description = "Preview do vídeo"


# --------------- PlanoEstudo ---------------

class PlanoEstudoCursoInline(admin.TabularInline):
    model = PlanoEstudoCurso
    extra = 0
    autocomplete_fields = ("curso",)
    fields = ("curso", "ordem", "obrigatorio")


@admin.register(PlanoEstudo)
class PlanoEstudoAdmin(admin.ModelAdmin):
    list_display = ("nome", "qtd_cursos", "obrigatorio", "ativo", "filial", "criado_em")
    list_filter = ("ativo", "obrigatorio", "filial")
    search_fields = ("nome", "descricao")
    autocomplete_fields = ("filial", "criado_por")
    readonly_fields = ("criado_em",)
    inlines = [PlanoEstudoCursoInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_total_cursos=Count("plano_cursos"))

    @admin.display(description="Cursos", ordering="_total_cursos")
    def qtd_cursos(self, obj):
        return obj._total_cursos


# --------------- MatriculaEAD ---------------

@admin.register(MatriculaEAD)
class MatriculaEADAdmin(admin.ModelAdmin):
    list_display = (
        "funcionario", "curso", "status", "progresso_bar",
        "nota_final", "ch_formatada", "data_matricula", "data_conclusao",
    )
    list_filter = ("status", "curso", "curso__filial", "data_matricula")
    search_fields = (
        "funcionario__nome", "funcionario__cpf",
        "curso__titulo",
    )
    autocomplete_fields = ("funcionario", "curso", "plano_estudo")
    readonly_fields = (
        "data_matricula", "data_conclusao",
        "progresso_percentual", "nota_final",
        "carga_horaria_cumprida_segundos", "tentativas_avaliacao",
    )
    date_hierarchy = "data_matricula"

    fieldsets = (
        ("Vínculo", {
            "fields": ("funcionario", "curso", "plano_estudo", "filial", "matriculado_por"),
        }),
        ("Status e Progresso", {
            "fields": (
                "status", "progresso_percentual", "nota_final",
                "tentativas_avaliacao", "carga_horaria_cumprida_segundos",
            ),
        }),
        ("Prazos", {
            "fields": ("prazo_limite",),
        }),
        ("Datas", {
            "fields": ("data_matricula", "data_conclusao"),
        }),
    )

    @admin.display(description="Progresso")
    def progresso_bar(self, obj):
        pct = float(obj.progresso_percentual or 0)
        color = "#28a745" if pct >= 100 else "#ffc107" if pct >= 50 else "#dc3545"
        return format_html(
            '<div style="width:100px;background:#e9ecef;border-radius:4px">'
            '<div style="width:{}%;background:{};padding:2px 6px;'
            'border-radius:4px;color:#fff;font-size:11px;text-align:center">'
            '{:.0f}%</div></div>',
            min(pct, 100), color, pct,
        )

    @admin.display(description="Carga Horária")
    def ch_formatada(self, obj):
        return obj.carga_horaria_cumprida_formatada


# --------------- ProgressoAulaEAD ---------------

@admin.register(ProgressoAulaEAD)
class ProgressoAulaEADAdmin(admin.ModelAdmin):
    list_display = (
        "matricula", "aula", "concluida",
        "percentual_assistido", "tempo_formatado", "concluido_em",
    )
    list_filter = ("concluida", "aula__modulo__curso")
    search_fields = (
        "matricula__funcionario__nome",
        "aula__titulo",
    )
    autocomplete_fields = ("matricula", "aula")
    readonly_fields = ("concluido_em", "ultimo_acesso")

    @admin.display(description="Tempo Gasto")
    def tempo_formatado(self, obj):
        return obj.tempo_gasto_formatado


# --------------- AvaliacaoEAD ---------------

class QuestaoEADInline(admin.TabularInline):
    model = QuestaoEAD
    extra = 0
    fields = ("ordem", "enunciado", "peso", "ativo")
    ordering = ("ordem",)
    show_change_link = True


@admin.register(AvaliacaoEAD)
class AvaliacaoEADAdmin(admin.ModelAdmin):
    list_display = (
        "titulo", "curso", "tempo_limite_min",
        "embaralhar_questoes", "qtd_questoes", "ativo",
    )
    list_filter = ("ativo", "curso")
    search_fields = ("titulo", "curso__titulo")
    autocomplete_fields = ("curso",)
    inlines = [QuestaoEADInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_total_questoes=Count("questoes_ead"))

    @admin.display(description="Questões", ordering="_total_questoes")
    def qtd_questoes(self, obj):
        return obj._total_questoes


# --------------- QuestaoEAD + Alternativas ---------------

class AlternativaEADInline(admin.TabularInline):
    model = AlternativaEAD
    extra = 4
    fields = ("ordem", "texto", "correta")


@admin.register(QuestaoEAD)
class QuestaoEADAdmin(admin.ModelAdmin):
    list_display = (
        "ordem", "enunciado_resumo", "avaliacao",
        "peso", "qtd_alternativas", "ativo",
    )
    list_filter = ("avaliacao__curso", "avaliacao", "ativo")
    search_fields = ("enunciado", "avaliacao__titulo")
    autocomplete_fields = ("avaliacao",)
    inlines = [AlternativaEADInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_total_alt=Count("alternativas_ead"))

    @admin.display(description="Alternativas", ordering="_total_alt")
    def qtd_alternativas(self, obj):
        return obj._total_alt

    @admin.display(description="Enunciado")
    def enunciado_resumo(self, obj):
        return obj.enunciado[:80] + "…" if len(obj.enunciado) > 80 else obj.enunciado


@admin.register(AlternativaEAD)
class AlternativaEADAdmin(admin.ModelAdmin):
    list_display = ("__str__", "questao", "correta")
    list_filter = ("correta", "questao__avaliacao")
    search_fields = ("texto", "questao__enunciado")
    autocomplete_fields = ("questao",)


# --------------- TentativaAvaliacaoEAD ---------------

class RespostaAlunoEADInline(admin.TabularInline):
    model = RespostaAlunoEAD
    extra = 0
    fields = ("questao", "alternativa_escolhida", "acertou")
    readonly_fields = ("acertou",)
    autocomplete_fields = ("questao", "alternativa_escolhida")

    @admin.display(description="Correta?", boolean=True)
    def acertou(self, obj):
        return obj.esta_correta


@admin.register(TentativaAvaliacaoEAD)
class TentativaAvaliacaoEADAdmin(admin.ModelAdmin):
    list_display = (
        "matricula", "avaliacao", "numero_tentativa",
        "nota", "aprovado", "iniciada_em", "finalizada_em",
    )
    list_filter = ("aprovado", "avaliacao__curso", "avaliacao")
    search_fields = (
        "matricula__funcionario__nome",
        "avaliacao__titulo",
    )
    autocomplete_fields = ("matricula", "avaliacao")
    readonly_fields = ("iniciada_em",)
    inlines = [RespostaAlunoEADInline]


@admin.register(RespostaAlunoEAD)
class RespostaAlunoEADAdmin(admin.ModelAdmin):
    list_display = ("tentativa", "questao", "alternativa_escolhida", "acertou")
    list_filter = ("tentativa__avaliacao",)
    search_fields = ("questao__enunciado",)
    autocomplete_fields = ("tentativa", "questao", "alternativa_escolhida")

    @admin.display(description="Correta?", boolean=True)
    def acertou(self, obj):
        return obj.esta_correta


# --------------- CertificadoEAD ---------------

@admin.register(CertificadoEAD)
class CertificadoEADAdmin(admin.ModelAdmin):
    list_display = (
        "nome_funcionario", "nome_curso", "nota",
        "ch_display", "uuid_curto",
        "data_emissao", "data_validade", "valido_badge", "link_download",
    )
    list_filter = ("data_emissao", "filial", "matricula__curso")
    search_fields = (
        "uuid", "nome_funcionario", "cpf_funcionario",
        "nome_curso",
    )
    autocomplete_fields = ("matricula",)
    readonly_fields = ("uuid", "data_emissao")
    date_hierarchy = "data_emissao"

    fieldsets = (
        ("Certificado", {
            "fields": ("uuid", "matricula", "arquivo_pdf"),
        }),
        ("Snapshot — Dados Congelados", {
            "fields": (
                "nome_funcionario", "cpf_funcionario",
                "nome_curso", "nome_tipo_curso", "nome_instrutor",
                "carga_horaria_exigida", "carga_horaria_cumprida", "nota",
            ),
        }),
        ("Validade", {
            "fields": ("data_emissao", "data_validade"),
        }),
        ("Controle", {
            "fields": ("filial", "emitido_por"),
        }),
    )

    @admin.display(description="Código")
    def uuid_curto(self, obj):
        return format_html(
            '<code style="font-size:12px">{}</code>',
            str(obj.uuid)[:8] + "…",
        )

    @admin.display(description="CH")
    def ch_display(self, obj):
        return f"{obj.carga_horaria_cumprida}/{obj.carga_horaria_exigida}h"

    @admin.display(description="Válido?", boolean=True)
    def valido_badge(self, obj):
        return obj.esta_valido

    @admin.display(description="Download")
    def link_download(self, obj):
        if obj.arquivo_pdf:
            return format_html(
                '<a href="{}" target="_blank">📄 PDF</a>',
                obj.arquivo_pdf.url,
            )
        return "—"


