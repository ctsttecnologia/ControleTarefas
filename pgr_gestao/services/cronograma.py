# pgr_gestao/services/cronograma.py
from pgr_gestao.constants import ACOES_PADRAO
from pgr_gestao.models import CronogramaAcaoPGR


def criar_cronograma_padrao(pgr):
    CronogramaAcaoPGR.objects.bulk_create([
        CronogramaAcaoPGR(
            pgr_documento=pgr,
            numero_item=n, acao_necessaria=acao, publico_alvo=publico,
            periodicidade=period, responsavel=resp,
            data_proxima_avaliacao=pgr.data_vencimento, status="pendente",
        )
        for n, acao, publico, period, resp in ACOES_PADRAO
    ])


