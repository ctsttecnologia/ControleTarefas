
# tarefas/signals.py
"""
Signals do app tarefas.

Responsabilidades:
1. Detectar mudança de status para 'concluida' e disparar geração
   da próxima ocorrência (se for tarefa recorrente).
2. Notificar interessados quando uma tarefa é criada.
3. Notificar mudança de status com participantes.
4. Registrar histórico v2 automaticamente.
"""

import logging

from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone

from .models import Tarefas, HistoricoTarefa, HistoricoStatus

logger = logging.getLogger(__name__)


# =============================================================================
# CACHE DO STATUS ANTERIOR (pre_save) — para detectar mudanças
# =============================================================================

@receiver(pre_save, sender=Tarefas)
def cache_status_anterior(sender, instance, **kwargs):
    """
    Antes de salvar, captura o status anterior para comparação no post_save.
    Armazena no próprio objeto como atributo temporário.
    """
    if instance.pk:
        try:
            anterior = Tarefas.objects.only('status', 'responsavel_id', 'prazo').get(pk=instance.pk)
            instance._status_anterior = anterior.status
            instance._responsavel_anterior_id = anterior.responsavel_id
            instance._prazo_anterior = anterior.prazo
        except Tarefas.DoesNotExist:
            instance._status_anterior = None
            instance._responsavel_anterior_id = None
            instance._prazo_anterior = None
    else:
        instance._status_anterior = None
        instance._responsavel_anterior_id = None
        instance._prazo_anterior = None


# =============================================================================
# AÇÕES PÓS-SALVAMENTO
# =============================================================================

@receiver(post_save, sender=Tarefas)
def acao_pos_save_tarefa(sender, instance, created, **kwargs):
    """
    Dispara ações conforme contexto:
    - Tarefa nova: notifica interessados
    - Mudança de status: notifica + gera recorrência se concluída
    """
    # Import lazy para evitar circular import
    from notifications.services import (
        notificar_tarefa_criada,
        notificar_tarefa_status_participantes,
        notificar_tarefa_recorrente_gerada,
    )

    status_anterior = getattr(instance, '_status_anterior', None)

    # ─── CASO 1: Tarefa recém-criada ──────────────────────────
    if created:
        # Marca a hora da conclusão se já nasceu concluída (raro)
        if instance.status == 'concluida' and not instance.concluida_em:
            Tarefas.objects.filter(pk=instance.pk).update(
                concluida_em=timezone.now()
            )

        # Notificação só faz sentido com responsável definido (m2m vem depois)
        # m2m_changed cuida dos participantes adicionados depois
        try:
            notificar_tarefa_criada(instance, instance.usuario)
        except Exception as e:
            logger.error(f'Erro ao notificar criação de tarefa #{instance.pk}: {e}', exc_info=True)

        return

    # ─── CASO 2: Mudança de status ────────────────────────────
    if status_anterior and status_anterior != instance.status:
        novo_status = instance.status

        # Marca data de conclusão se mudou para concluída
        if novo_status == 'concluida' and not instance.concluida_em:
            Tarefas.objects.filter(pk=instance.pk).update(
                concluida_em=timezone.now()
            )

        # Registrar histórico legado (compatibilidade)
        try:
            HistoricoStatus.objects.create(
                tarefa=instance,
                status_anterior=status_anterior,
                novo_status=novo_status,
                alterado_por=getattr(instance, '_alterado_por', None),
                filial=instance.filial,
            )
        except Exception as e:
            logger.error(f'Erro ao registrar histórico de status: {e}', exc_info=True)

        # Notificar mudança de status (sino + e-mail)
        try:
            display_anterior = dict(Tarefas.STATUS_CHOICES).get(status_anterior, status_anterior)
            display_novo = dict(Tarefas.STATUS_CHOICES).get(novo_status, novo_status)
            notificar_tarefa_status_participantes(
                tarefa=instance,
                status_anterior=display_anterior,
                novo_status=display_novo,
                alterado_por=getattr(instance, '_alterado_por', None),
            )
        except Exception as e:
            logger.error(f'Erro ao notificar mudança de status #{instance.pk}: {e}', exc_info=True)

        # ⭐ GERAÇÃO DE RECORRÊNCIA ao concluir
        if novo_status == 'concluida':
            try:
                gerar_recorrencia_se_aplicavel(instance)
            except Exception as e:
                logger.error(
                    f'Erro ao gerar recorrência da tarefa #{instance.pk}: {e}',
                    exc_info=True
                )


# =============================================================================
# GERAÇÃO DE RECORRÊNCIA — Lógica isolada para reuso
# =============================================================================

def gerar_recorrencia_se_aplicavel(tarefa):
    """
    Verifica se a tarefa concluída deve gerar próxima ocorrência
    e, em caso positivo, cria a nova tarefa + notifica.
    
    Funciona tanto para:
    - Tarefas-RAIZ (recorrente=True): geram própria continuação
    - Tarefas-FILHA (têm pai): pedem ao pai para gerar próxima
    """
    from notifications.services import notificar_tarefa_recorrente_gerada

    # Só age se a tarefa pertence a uma cadeia de recorrência
    if not (tarefa.recorrente or tarefa.is_filha_recorrencia):
        return None

    raiz = tarefa.tarefa_raiz

    # Validação centralizada no model
    pode, motivo = tarefa.pode_gerar_proxima()
    if not pode:
        logger.info(
            f'Recorrência não gerada para tarefa #{tarefa.pk} (raiz #{raiz.pk}): {motivo}'
        )
        return None

    nova = tarefa.gerar_proxima_ocorrencia()
    if not nova:
        return None

    logger.info(
        f'✅ Nova ocorrência #{nova.pk} gerada a partir da raiz #{raiz.pk} '
        f'(prazo: {nova.prazo})'
    )

    # Notificar interessados sobre a nova ocorrência
    try:
        notificar_tarefa_recorrente_gerada(tarefa_nova=nova, tarefa_raiz=raiz)
    except Exception as e:
        logger.error(
            f'Erro ao notificar recorrência gerada #{nova.pk}: {e}',
            exc_info=True
        )

    return nova


# =============================================================================
# PARTICIPANTES — m2m_changed
# =============================================================================

@receiver(m2m_changed, sender=Tarefas.participantes.through)
def notificar_participantes_adicionados(sender, instance, action, pk_set, **kwargs):
    """
    Quando participantes são adicionados a uma tarefa existente,
    notifica os novos participantes.
    
    Não dispara em tarefas recém-criadas (notificar_tarefa_criada já cuida).
    """
    if action != 'post_add' or not pk_set:
        return

    # Evita notificação duplicada em tarefas recém-criadas
    # (delta de 5 segundos entre criação e adição de participantes)
    if instance.data_criacao:
        delta = (timezone.now() - instance.data_criacao).total_seconds()
        if delta < 5:
            return

    from django.contrib.auth import get_user_model
    from notifications.services import notificar_tarefa_participante_adicionado

    User = get_user_model()
    novos = User.objects.filter(pk__in=pk_set)

    if not novos.exists():
        return

    try:
        notificar_tarefa_participante_adicionado(
            tarefa=instance,
            novos_participantes=novos,
            adicionado_por=getattr(instance, '_alterado_por', None),
        )
    except Exception as e:
        logger.error(
            f'Erro ao notificar participantes adicionados na tarefa #{instance.pk}: {e}',
            exc_info=True
        )

