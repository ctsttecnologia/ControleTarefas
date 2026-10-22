
# =============================================================================
# gestao_riscos/context_processors.py
# =============================================================================
from django.core.cache import cache
from django.utils import timezone

from core.utils import get_filial_ativa

CACHE_TTL = 60 * 15


def dias_sem_acidentes(request):
    """Roda em TODA request → resultado cacheado por filial (invalidado via signal)."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    filial = get_filial_ativa(user, request)
    if not filial:
        return {'dias_sem_acidentes': 0, 'data_ultimo_acidente': None}

    def _calcular():
        from .models import Incidente, TIPOS_ZERAM_CONTADOR
        base = Incidente.objects.filter(filial=filial)
        ultimo = (base.filter(tipo_ocorrencia__in=TIPOS_ZERAM_CONTADOR)
                  .order_by('-data_ocorrencia').values_list('data_ocorrencia', flat=True).first())
        ref = ultimo or base.order_by('data_registro').values_list('data_registro', flat=True).first()
        return {'ref': ref, 'ultimo': ultimo}

    from .models import dias_sem_acidentes_cache_key
    dados = cache.get_or_set(dias_sem_acidentes_cache_key(filial.pk), _calcular, CACHE_TTL)

    ref = dados['ref']
    dias = (timezone.localdate() - timezone.localtime(ref).date()).days if ref else 0
    return {'dias_sem_acidentes': max(dias, 0), 'data_ultimo_acidente': dados['ultimo']}

