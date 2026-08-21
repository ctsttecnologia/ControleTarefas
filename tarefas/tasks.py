
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
from django.utils import timezone


logger = logging.getLogger(__name__)


# =============================================================================
# HELPERS
# =============================================================================

def _garantir_aware(dt):
    """
    Garante datetime 'aware' quando USE_TZ está ativo, para comparações
    seguras com timezone.now() (evita TypeError em dados legacy 'naive').
    Assume que valores 'naive' estão no timezone local (TIME_ZONE).
    """
    if dt is None:
        return None
    if settings.USE_TZ and timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


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
    - Máximo TAREFAS_MAX_RECORRENCIAS_POR_EXECUCAO por execução
    - Respeita MAX_RECORRENCIAS_POR_RAIZ do model
    """
    from .models import Tarefas
    from .signals import gerar_recorrencia_se_aplicavel

    limite_execucao = getattr(
        settings, 'TAREFAS_MAX_RECORRENCIAS_POR_EXECUCAO', 50
    )

    raizes_ativas = Tarefas.objects.filter(
        recorrente=True,
        recorrencia_encerrada=False,
        tarefa_recorrencia_pai__isnull=True,
    ).exclude(
        status__in=('cancelada',)
    )

    agora = timezone.now()
    total_candidatas = raizes_ativas.count()

    geradas = 0
    erros = 0
    encerradas = 0
    verificadas = 0

    for raiz in raizes_ativas.iterator():
        if geradas >= limite_execucao:
            logger.warning(
                f'Limite de {limite_execucao} recorrências por execução atingido. '
                f'Restantes serão processadas na próxima execução.'
            )
            break

        verificadas += 1

        try:
            ultima = raiz.recorrencias_filhas.order_by('-prazo').first() or raiz

            # Se a última ainda está no futuro, não precisa gerar agora
            prazo_ultima = _garantir_aware(ultima.prazo)
            if prazo_ultima and prazo_ultima > agora:
                continue

            # Regra de geração:
            # - Com ocorrências filhas: só gera a próxima se a última estiver
            #   concluída/cancelada.
            # - Raiz que NUNCA gerou ocorrência e já está vencida: gera a
            #   primeira (exceção para não travar a recorrência).
            if ultima.pk != raiz.pk and ultima.status not in ('concluida', 'cancelada'):
                continue

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
        'total_raizes_verificadas': verificadas,
        'total_raizes_candidatas': total_candidatas,
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

    candidatas = Tarefas.objects.filter(
        dias_lembrete__gt=0,
        prazo__isnull=False,
        lembrete_enviado_em__isnull=True,
    ).exclude(
        status__in=('concluida', 'cancelada')
    ).select_related('responsavel', 'usuario')

    total_candidatas = candidatas.count()
    enviados = 0
    erros = 0

    for tarefa in candidatas.iterator():
        try:
            prazo_aware = _garantir_aware(tarefa.prazo)
            data_alvo_lembrete = prazo_aware - timedelta(days=tarefa.dias_lembrete)

            # Ainda não chegou a hora de avisar
            if agora < data_alvo_lembrete:
                continue

            # Passou mais de 1 dia do prazo: outras rotinas cuidam; marca e segue
            if agora - prazo_aware > timedelta(days=1):
                Tarefas.objects.filter(
                    pk=tarefa.pk, lembrete_enviado_em__isnull=True
                ).update(lembrete_enviado_em=agora)
                continue

            # Reivindica de forma atômica (evita envio duplicado em execuções concorrentes)
            claimed = Tarefas.objects.filter(
                pk=tarefa.pk, lembrete_enviado_em__isnull=True
            ).update(lembrete_enviado_em=agora)

            if not claimed:
                continue  # outra execução já processou

            try:
                dias_antes = max(0, (prazo_aware - agora).days)
                notificar_lembrete_tarefa_prazo(
                    tarefa=tarefa,
                    dias_antes=dias_antes,
                )
                enviados += 1
            except Exception:
                # Reverte a marcação para permitir nova tentativa na próxima execução
                Tarefas.objects.filter(pk=tarefa.pk).update(lembrete_enviado_em=None)
                raise

        except Exception as e:
            erros += 1
            logger.error(
                f'[Lembretes] Erro ao processar tarefa #{tarefa.pk}: {e}',
                exc_info=True
            )

    resultado = {
        'enviados': enviados,
        'erros': erros,
        'total_candidatas': total_candidatas,
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

    candidatas = Tarefas.objects.filter(
        recorrente=True,
        recorrencia_encerrada=False,
        tarefa_recorrencia_pai__isnull=True,
        data_fim_recorrencia__isnull=False,
        aviso_fim_enviado_em__isnull=True,
    ).select_related('usuario', 'responsavel')

    total_candidatas = candidatas.count()
    avisos_enviados = 0
    erros = 0
    detalhes = []

    for raiz in candidatas.iterator():
        try:
            dias_restantes = (raiz.data_fim_recorrencia - hoje).days
            # Corrigido: 0 é valor válido ("avisar no próprio dia"); o `or`
            # anterior tratava 0 como ausência e caía no padrão.
            limite_aviso = (
                raiz.dias_aviso_fim_recorrencia
                if raiz.dias_aviso_fim_recorrencia is not None
                else Tarefas.DIAS_AVISO_FIM_PADRAO
            )

            if dias_restantes > limite_aviso:
                continue

            # Data fim já passou: encerra a recorrência e não avisa
            if dias_restantes < 0:
                Tarefas.objects.filter(pk=raiz.pk).update(
                    recorrencia_encerrada=True,
                    aviso_fim_enviado_em=agora,
                )
                continue

            # Reivindica de forma atômica (evita aviso duplicado em concorrência)
            claimed = Tarefas.objects.filter(
                pk=raiz.pk, aviso_fim_enviado_em__isnull=True
            ).update(aviso_fim_enviado_em=agora)

            if not claimed:
                continue

            try:
                notificar_recorrencia_proxima_fim(
                    tarefa_raiz=raiz,
                    dias_restantes=dias_restantes,
                )
                avisos_enviados += 1
                detalhes.append({
                    'tarefa_id': raiz.pk,
                    'titulo': raiz.titulo,
                    'dias_restantes': dias_restantes,
                })
            except Exception:
                Tarefas.objects.filter(pk=raiz.pk).update(aviso_fim_enviado_em=None)
                raise

        except Exception as e:
            erros += 1
            logger.error(
                f'[Aviso Fim Recorrência] Erro ao processar raiz #{raiz.pk}: {e}',
                exc_info=True
            )

    resultado = {
        'avisos_enviados': avisos_enviados,
        'total_avisados': avisos_enviados,    # alias p/ command
        'total': avisos_enviados,             # alias genérico
        'erros': erros,
        'total_candidatas': total_candidatas,
        'avisos': detalhes,                   # p/ --verbose
    }
    logger.info(f'[Aviso Fim Recorrência] Concluído: {resultado}')
    return resultado


# ─── Alias público (compatibilidade com command/agendadores externos) ──────
avisar_fim_recorrencia = avisar_recorrencias_proximas_fim


# =============================================================================
# TASK 4 — Marcar tarefas atrasadas automaticamente
# =============================================================================

def _marcar_atrasadas_logica(agora=None):
    """
    Lógica pura e reutilizável.
    Retorna o queryset de tarefas atrasadas (prazo no passado e status ativo).
    """
    from .models import Tarefas

    if agora is None:
        agora = timezone.now()

    return Tarefas.objects.filter(
        prazo__lt=agora,
        status__in=('pendente', 'andamento', 'pausada'),
    )


@shared_task(name='tarefas.marcar_tarefas_atrasadas')
def marcar_tarefas_atrasadas():
    """
    Atualiza status para 'atrasada' em tarefas:
    - Com prazo no passado
    - Status atual: pendente, andamento ou pausada
    - Não concluída/cancelada

    Usa update() em massa (sem disparar signals — atualização técnica).
    """
    qs = _marcar_atrasadas_logica()

    # update() já retorna o nº de linhas afetadas — evita count() extra e race condition
    atualizadas = qs.update(status='atrasada')

    if atualizadas == 0:
        logger.info('[Tarefas Atrasadas] Nenhuma tarefa para atualizar.')
    else:
        logger.info(f'[Tarefas Atrasadas] {atualizadas} tarefa(s) marcadas como atrasadas.')

    return {'atualizadas': atualizadas}


# =============================================================================
# TASK MANUAL — Para invocar manualmente em caso de necessidade
# =============================================================================

@shared_task(name='tarefas.executar_rotinas_manuais')
def executar_rotinas_manuais():
    """
    Executa todas as rotinas em sequência (útil para testes ou recuperação).
    Não usar em produção agendado — use as tasks individuais via Beat.
    """
    rotinas = {
        'atrasadas': marcar_tarefas_atrasadas,
        'recorrencias': gerar_recorrencias_pendentes,
        'lembretes': enviar_lembretes_prazo,
        'aviso_fim': avisar_recorrencias_proximas_fim,
    }

    resultados = {}
    for nome, rotina in rotinas.items():
        try:
            resultados[nome] = rotina.apply().get()
        except Exception as e:
            # Uma falha não deve impedir as demais rotinas
            resultados[nome] = {'erro': str(e)}
            logger.error(f'[Rotinas Manuais] Falha em {nome}: {e}', exc_info=True)

    logger.info(f'[Rotinas Manuais] Resultado completo: {resultados}')
    return resultados


