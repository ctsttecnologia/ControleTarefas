
# pgr_gestao/services/plano_acao.py
from datetime import timedelta
from django.utils import timezone
from pgr_gestao.models import PlanoAcaoPGR
from .risco import PRAZO_DIAS


def prazo_para(classificacao):
    return timezone.localdate() + timedelta(days=PRAZO_DIAS.get(classificacao, 180))


def criar_plano_automatico(risco):
    if risco.planos_acao.exists():
        return None
    return PlanoAcaoPGR.objects.create(
        filial=risco.filial,
        risco_identificado=risco,
        tipo_acao="controle_engenharia",
        descricao_acao=f"Implementar medidas de controle para o risco: {risco.agente}",
        prioridade="critica" if risco.classificacao_risco == "critico" else "alta",
        data_prevista=prazo_para(risco.classificacao_risco),
        responsavel="Coordenador de Segurança",
        status="pendente",
        criado_por=getattr(risco, "criado_por", None),
    )

