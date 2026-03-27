
# gestao_riscos/context_processors.py

from django.utils import timezone
from .models import Incidente


def dias_sem_acidentes(request):
    """Disponibiliza dias_sem_acidentes em TODOS os templates (header incluso)."""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {}

    filial_ativa = getattr(request.user, 'filial_ativa', None)
    if not filial_ativa:
        return {'dias_sem_acidentes': 0, 'data_ultimo_acidente': None}

    ultimo_acidente = Incidente.objects.filter(
        filial=filial_ativa,
        classificacao='COM_AFASTAMENTO'  # ← COM ACENTO, como está no model
    ).order_by('-data_ocorrencia').first()

    if ultimo_acidente and ultimo_acidente.data_ocorrencia:
        data_ref = ultimo_acidente.data_ocorrencia
        if hasattr(data_ref, 'date'):
            data_ref = data_ref.date()
        dias = (timezone.now().date() - data_ref).days
        data_ultimo = ultimo_acidente.data_ocorrencia
    else:
        primeiro_registro = Incidente.objects.filter(
            filial=filial_ativa
        ).order_by('data_registro').first()

        if primeiro_registro:
            data_ref = primeiro_registro.data_registro
            if hasattr(data_ref, 'date'):
                data_ref = data_ref.date()
            dias = (timezone.now().date() - data_ref).days
        else:
            dias = 0
        data_ultimo = None

    return {
        'dias_sem_acidentes': dias,
        'data_ultimo_acidente': data_ultimo,
    }
