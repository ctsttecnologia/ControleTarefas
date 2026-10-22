
import logging
from collections import Counter
from datetime import timedelta

from django.db.models import Exists, OuterRef
from django.utils import timezone

from seguranca_trabalho.models import EntregaEPI
from .models import Inspecao

logger = logging.getLogger(__name__)
HORIZONTE_DIAS = 7


def propor_inspecoes(filial=None):
    """Cria propostas na meia-vida do EPI e avisa a Segurança do Trabalho. Retorna a quantidade criada."""
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=HORIZONTE_DIAS)

    ja = Inspecao.objects.filter(
        entrega_epi=OuterRef('pk'),
        status__in=['PENDENTE_APROVACAO', 'PENDENTE', 'CONCLUIDA'],
    )
    qs = (EntregaEPI.objects
          .filter(data_devolucao__isnull=True,
                  equipamento__requer_numero_serie=True,
                  equipamento__vida_util_dias__gt=0)
          .annotate(ja=Exists(ja)).filter(ja=False)
          .select_related('equipamento', 'filial'))
    if filial:
        qs = qs.filter(filial=filial)

    por_filial = Counter()
    filiais = {}
    for item in qs.iterator():
        d = item.data_entrega
        if hasattr(d, 'date'):
            d = timezone.localtime(d).date()
        meia_vida = d + timedelta(days=item.equipamento.vida_util_dias // 2)
        if meia_vida <= limite:
            Inspecao.objects.create(
                entrega_epi=item, equipamento=item.equipamento, filial=item.filial,
                data_agendada=max(meia_vida, hoje), status='PENDENTE_APROVACAO',
                observacoes=f"Inspeção automática proposta (meia-vida do item N/S: {item.numero_serie or 'N/A'}).",
            )
            por_filial[item.filial_id] += 1
            filiais[item.filial_id] = item.filial

    # Notifica o sino (uma notificação por usuário e por filial)
    from notifications.services import notificar_inspecoes_propostas
    for fid, qtd in por_filial.items():
        try:
            notificar_inspecoes_propostas(filiais[fid], qtd)
        except Exception:
            logger.exception('Falha ao notificar propostas da filial %s', fid)

    return sum(por_filial.values())
