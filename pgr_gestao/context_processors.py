# pgr_gestao/context_processors.py
from django.core.cache import cache
from .selectors import documentos_visiveis, riscos_visiveis, planos_visiveis


def pgr_context(request):
    return {"PGR_APP_NAME": "PGR - Programa de Gerenciamento de Riscos",
            "PGR_VERSION": "1.0", "pgr_active": True}


def pgr_stats(request):
    """Registrar também em settings. Só roda dentro do módulo, com cache curto."""
    match = getattr(request, "resolver_match", None)
    if not request.user.is_authenticated or not match or match.namespace != "pgr_gestao":
        return {}
    filial = getattr(request, "filial_ativa", None)
    key = f"pgr_stats:{request.user.pk}:{getattr(filial, 'pk', 'all')}"
    stats = cache.get(key)
    if stats is None:
        planos = planos_visiveis(request)
        stats = {
            "total_documentos_pgr": documentos_visiveis(request).count(),
            "total_riscos_identificados": riscos_visiveis(request).count(),
            "total_planos_acao": planos.count(),
            "planos_acao_pendentes": planos.filter(
                status__in=["pendente", "em_andamento"]).count(),
        }
        cache.set(key, stats, 60)
    return {"pgr_stats": stats, "pgr_module_active": True}
