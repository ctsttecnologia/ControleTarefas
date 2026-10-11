"""
Fonte única de escopo (filial + técnico) e ordenação por severidade.
Todas as views, relatórios e exportações do PGR devem consultar por aqui.
"""
from django.db.models import Case, IntegerField, Value, When

from pgr_gestao.models import (
    AnexoPGR,
    AvaliacaoQuantitativa,
    CronogramaAcaoPGR,
    GESGrupoExposicao,
    PGRDocumento,
    PGRRevisao,
    PlanoAcaoPGR,
    RiscoIdentificado,
)

PERM_ALL_DOC = "pgr_gestao.view_all_pgrdocumento"

ORDEM_PRIORIDADE = {"critica": 4, "alta": 3, "media": 2, "baixa": 1}
ORDEM_CLASSIFICACAO = {
    "critico": 5, "muito_grave": 4, "moderado": 3, "marginal": 2, "negligenciavel": 1,
}


def escopo_total(user, permission=PERM_ALL_DOC):
    """True = vê todos os documentos da filial; False = só os que criou (técnico)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    if permission and user.has_perm(permission):
        return True
    if not hasattr(user, "_pgr_tecnico"):
        user._pgr_tecnico = user.groups.filter(name="TÉCNICO").exists()
    return not user._pgr_tecnico


def documentos_visiveis(request):
    qs = PGRDocumento.objects.for_request(request)
    if escopo_total(request.user):
        return qs
    return qs.filter(criado_por=request.user)


def _docs_pk(request):
    return documentos_visiveis(request).order_by().values("pk")


def ges_visiveis(request):
    return GESGrupoExposicao.objects.for_request(request).filter(
        pgr_documento__in=_docs_pk(request))


def revisoes_visiveis(request):
    return PGRRevisao.objects.for_request(request).filter(
        pgr_documento__in=_docs_pk(request))


def riscos_visiveis(request):
    return RiscoIdentificado.objects.for_request(request).filter(
        pgr_documento__in=_docs_pk(request))


def planos_visiveis(request):
    return PlanoAcaoPGR.objects.for_request(request).filter(
        risco_identificado__pgr_documento__in=_docs_pk(request))


def avaliacoes_visiveis(request):
    return AvaliacaoQuantitativa.objects.filter(
        risco_identificado__pgr_documento__in=_docs_pk(request))


def cronograma_visiveis(request):
    return CronogramaAcaoPGR.objects.filter(pgr_documento__in=_docs_pk(request))


def anexos_pgr_visiveis(request):
    return AnexoPGR.objects.filter(pgr_documento__in=_docs_pk(request))


def ordenar_por(qs, campo, mapa, *extra):
    """Ordena por severidade real (e não alfabética), do mais grave ao menos grave."""
    ordem = Case(
        *[When(**{campo: k}, then=Value(v)) for k, v in mapa.items()],
        default=Value(0), output_field=IntegerField(),
    )
    return qs.annotate(_ord=ordem).order_by("-_ord", *extra)


def ordenar_riscos(qs, *extra):
    return ordenar_por(qs, "classificacao_risco", ORDEM_CLASSIFICACAO, *extra)


def ordenar_planos(qs, *extra):
    return ordenar_por(qs, "prioridade", ORDEM_PRIORIDADE, *extra)

