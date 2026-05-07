
# tarefas/tasks.py
"""
Tasks Celery para o app tarefas.

Tasks agendadas (Celery Beat):
- gerar_recorrencias_pendentes: fallback diário 02:00
- enviar_lembretes_prazo: diariamente 08:00
- avisar_recorrencias_proximas_fim: semanalmente segunda 09:00
- marcar_tarefas_atrasadas: diariamente 00:30
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# TASK 1 — Fallback de geração de recorrências
# =============================================================================

@shared_task(name='tarefas.gerar_recorrencias_pendentes')
def gerar_recorrencias_pendentes():
    """
    FALLBACK diário: garante que recorrências sejam geradas mesmo se
    o signal de conclusão falhar ou se uma ocorrência ficar "esquecida".
    
    Para cada tarefa-RAIZ ativa, verifica se a última ocorrência (ou ela mesma)
    tem prazo no passado E não há próxima ocorrência criada → gera.
    
    Limites de segurança:
    - Máximo MAX_RECORRENCIAS_POR_EXECUCAO recorrências geradas por execução
    - Respeita MAX_RECORRENCIAS_POR_RAIZ do model
    """
    from .models import Tarefas
    from .signals import gerar_recorrencia_se_aplicavel

    limite_execucao = getattr(
        settings, 'TAREFAS_MAX_RECORRENCIAS_POR_EXECUCAO', 50
    )

    # Buscar todas as tarefas-RAIZ ativas
    raizes_ativas = Tarefas.objects.filter(
        recorrente=True,
        recorrencia_encerrada=False,
        tarefa_recorrencia_pai__isnull=True,
    ).exclude(
        status__in=('cancelada',)
    )

    geradas = 0
    erros = 0
    encerradas = 0

    for raiz in raizes_ativas:
        if geradas >= limite_execucao:
            logger.warning(
                f'Limite de {limite_execucao} recorrências por execução atingido. '
                f'Restantes serão processadas na próxima execução.'
            )
            break

        try:
            # Pega a última ocorrência da cadeia (filha mais recente ou a própria raiz)
            ultima = raiz.recorrencias_filhas.order_by('-prazo').first() or raiz

            # Se a última ainda está no futuro, não precisa gerar agora
            if ultima.prazo and ultima.prazo > timezone.now():
                continue

            # Se a última já está concluída/cancelada, gera próxima a partir dela
            # Se está pendente/atrasada e prazo passou, não geramos (espera ser concluída)
            # EXCETO se a raiz tem prazo já vencido e nunca gerou nada
            if ultima.status not in ('concluida', 'cancelada'):
                continue

            # Validação completa via método do model
            pode, motivo = ultima.pode_gerar_proxima()
            if not pode:
                if 'fim' in motivo.lower() or 'limite' in motivo.lower():
                    encerradas += 1
                continue

            nova = gerar_recorrencia_se_aplicavel(ultima)
            if nova:
                geradas += 1
                logger.info(
                    f'[Fallback] Recorrência gerada: tarefa #{nova.pk} '
                    f'(raiz #{raiz.pk}, prazo: {nova.prazo})'
                )

        except Exception as e:
            erros += 1
            logger.error(
                f'[Fallback] Erro ao processar raiz #{raiz.pk}: {e}',
                exc_info=True
            )

    resultado = {
        'geradas': geradas,
        'encerradas': encerradas,
        'erros': erros,
        'total_raizes_verificadas': raizes_ativas.count(),
    }
    logger.info(f'[Fallback Recorrências] Concluído: {resultado}')
    return resultado


# =============================================================================
# TASK 2 — Lembretes de prazo
# =============================================================================

@shared_task(name='tarefas.enviar_lembretes_prazo')
def enviar_lembretes_prazo():
    """
    Envia lembretes para tarefas com prazo próximo, conforme campo `dias_lembrete`.
    
    Lógica:
    - Para cada tarefa ativa com dias_lembrete > 0
    - Calcula data alvo do lembrete = prazo - dias_lembrete dias
    - Se hoje >= data_alvo E lembrete_enviado_em IS NULL → envia e marca
    """
    from .models import Tarefas
    from notifications.services import notificar_lembrete_tarefa_prazo

    agora = timezone.now()
    hoje = agora.date()

    # Tarefas candidatas: ativas, com prazo, com lembrete configurado, ainda não enviado
    candidatas = Tarefas.objects.filter(
        dias_lembrete__gt=0,
        prazo__isnull=False,
        lembrete_enviado_em__isnull=True,
    ).exclude(
        status__in=('concluida', 'cancelada')
    ).select_related('responsavel', 'usuario')

    enviados = 0
    erros = 0

    for tarefa in candidatas:
        try:
            data_alvo_lembrete = tarefa.prazo - timedelta(days=tarefa.dias_lembrete)

            # Hora de enviar?
            if agora < data_alvo_lembrete:
                continue

            # Se já passou do prazo, ainda envia (com urgência)
            dias_ate_prazo = (tarefa.prazo - agora).days

            # Não envia se já passou MUITO do prazo (mais de 1 dia atrasada)
            # — outras notificações cuidam disso
            if dias_ate_prazo < -1:
                # Marca como enviado para não tentar de novo
                Tarefas.objects.filter(pk=tarefa.pk).update(
                    lembrete_enviado_em=agora
                )
                continue

            # Envia lembrete
            notificar_lembrete_tarefa_prazo(
                tarefa=tarefa,
                dias_antes=max(dias_ate_prazo, 0),
            )

            # Marca como enviado (envio único)
            Tarefas.objects.filter(pk=tarefa.pk).update(
                lembrete_enviado_em=agora
            )
            enviados += 1

        except Exception as e:
            erros += 1
            logger.error(
                f'[Lembretes] Erro ao processar tarefa #{tarefa.pk}: {e}',
                exc_info=True
            )

    resultado = {
        'enviados': enviados,
        'erros': erros,
        'total_candidatas': candidatas.count(),
    }
    logger.info(f'[Lembretes Prazo] Concluído: {resultado}')
    return resultado


# =============================================================================
# TASK 3 — Aviso de fim de recorrência
# =============================================================================

@shared_task(name='tarefas.avisar_recorrencias_proximas_fim')
def avisar_recorrencias_proximas_fim():
    """
    Verifica tarefas-RAIZ recorrentes cujo `data_fim_recorrencia` está próximo
    e ainda não foram avisadas.
    
    Usa o campo `dias_aviso_fim_recorrencia` de cada tarefa (configurável).
    """
    from .models import Tarefas
    from notifications.services import notificar_recorrencia_proxima_fim

    agora = timezone.now()
    hoje = agora.date()

    # Tarefas-RAIZ recorrentes ativas com data fim definida e aviso ainda não enviado
    candidatas = Tarefas.objects.filter(
        recorrente=True,
        recorrencia_encerrada=False,
        tarefa_recorrencia_pai__isnull=True,
        data_fim_recorrencia__isnull=False,
        aviso_fim_enviado_em__isnull=True,
    ).select_related('usuario', 'responsavel')

    # Substituir linhas 222-267
    avisos_enviados = 0
    erros = 0
    detalhes = []   # ← novo

    for raiz in candidatas:
        try:
            dias_restantes = (raiz.data_fim_recorrencia - hoje).days
            limite_aviso = raiz.dias_aviso_fim_recorrencia or Tarefas.DIAS_AVISO_FIM_PADRAO

            if dias_restantes > limite_aviso:
                continue

            if dias_restantes < 0:
                Tarefas.objects.filter(pk=raiz.pk).update(
                    recorrencia_encerrada=True,
                    aviso_fim_enviado_em=agora,
                )
                continue

            notificar_recorrencia_proxima_fim(
                tarefa_raiz=raiz,
                dias_restantes=dias_restantes,
            )

            Tarefas.objects.filter(pk=raiz.pk).update(
                aviso_fim_enviado_em=agora
            )
            avisos_enviados += 1
            detalhes.append({
                'tarefa_id': raiz.pk,
                'titulo': raiz.titulo,
                'ocorrencias_restantes': dias_restantes,
            })

        except Exception as e:
            erros += 1
            logger.error(
                f'[Aviso Fim Recorrência] Erro ao processar raiz #{raiz.pk}: {e}',
                exc_info=True
            )

    resultado = {
        'avisos_enviados': avisos_enviados,
        'total_avisados': avisos_enviados,    # ← alias p/ command
        'total': avisos_enviados,             # ← alias genérico
        'erros': erros,
        'total_candidatas': candidatas.count(),
        'avisos': detalhes,                   # ← p/ --verbose
    }
    logger.info(f'[Aviso Fim Recorrência] Concluído: {resultado}')
    return resultado


# ─── Alias público (compatibilidade com command/agendadores externos) ──────
# O command `executar_rotinas_tarefas` e jobs do Celery Beat importam pelo
# nome curto `avisar_fim_recorrencia`. Mantemos os dois para não quebrar
# integrações antigas nem novas.
avisar_fim_recorrencia = avisar_recorrencias_proximas_fim


# =============================================================================
# TASK 4 — Marcar tarefas atrasadas automaticamente
# =============================================================================

@shared_task(name='tarefas.marcar_tarefas_atrasadas')
def marcar_tarefas_atrasadas():
    """
    Atualiza status para 'atrasada' em tarefas:
    - Com prazo no passado
    - Status atual: pendente, andamento ou pausada
    - Não concluída/cancelada
    
    Usa update() em massa (sem disparar signals — atualização técnica).
    """
    from .models import Tarefas

    agora = timezone.now()

    # Marca como atrasadas
    qs = Tarefas.objects.filter(
        prazo__lt=agora,
        status__in=('pendente', 'andamento', 'pausada'),
    )

    total = qs.count()
    if total == 0:
        logger.info('[Tarefas Atrasadas] Nenhuma tarefa para atualizar.')
        return {'atualizadas': 0}

    # update() em massa — não dispara signals (intencional)
    atualizadas = qs.update(status='atrasada')

    logger.info(f'[Tarefas Atrasadas] {atualizadas} tarefa(s) marcadas como atrasadas.')
    return {'atualizadas': atualizadas, **_marcar_atrasadas_logica()}

def _marcar_atrasadas_logica():
    """Lógica pura, reutilizável."""
    # ... seu código aqui
    return {"atualizadas": 42}

# =============================================================================
# TASK MANUAL — Para invocar manualmente em caso de necessidade
# =============================================================================

@shared_task(name='tarefas.executar_rotinas_manuais')
def executar_rotinas_manuais():
    """
    Executa todas as rotinas em sequência (útil para testes ou recuperação).
    Não usar em produção agendado — use as tasks individuais via Beat.
    """
    resultados = {
        'atrasadas': marcar_tarefas_atrasadas.apply().get(),
        'recorrencias': gerar_recorrencias_pendentes.apply().get(),
        'lembretes': enviar_lembretes_prazo.apply().get(),
        'aviso_fim': avisar_recorrencias_proximas_fim.apply().get(),
    }
    logger.info(f'[Rotinas Manuais] Resultado completo: {resultados}')
    return resultados

