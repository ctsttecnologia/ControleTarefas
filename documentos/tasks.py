
# documentos/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Documento

logger = logging.getLogger(__name__)

DIAS_AVISO_PREVIO = 30


@shared_task(name="documentos.verificar_vencimentos")
def verificar_vencimentos_documentos():
    """Verifica diariamente documentos vencidos e a vencer."""
    hoje = timezone.now().date()
    data_limite_aviso = hoje + timedelta(days=DIAS_AVISO_PREVIO)

    logger.info(f"[Documentos] Verificação de vencimentos iniciada em {hoje}")

    # 1. Marcar como VENCIDO
    vencidos = Documento.objects.filter(
        data_vencimento__lt=hoje,
        status__in=[Documento.StatusChoices.VIGENTE, Documento.StatusChoices.A_VENCER],
    )

    count_vencidos = 0
    for doc in vencidos:
        doc.status = Documento.StatusChoices.VENCIDO
        doc.save(update_fields=['status'])
        _criar_notificacao_documento(doc, 'vencido')
        count_vencidos += 1

    # 2. Marcar como A_VENCER
    a_vencer = Documento.objects.filter(
        data_vencimento__gte=hoje,
        data_vencimento__lte=data_limite_aviso,
        status=Documento.StatusChoices.VIGENTE,
    )

    count_a_vencer = 0
    for doc in a_vencer:
        doc.status = Documento.StatusChoices.A_VENCER
        doc.save(update_fields=['status'])
        _criar_notificacao_documento(doc, 'a_vencer')
        count_a_vencer += 1

    logger.info(f"[Documentos] Concluído: {count_vencidos} vencidos, {count_a_vencer} a vencer.")
    return f"Concluído: {count_vencidos} vencidos, {count_a_vencer} a vencer."


def _criar_notificacao_documento(doc, tipo):
    """Cria notificação no sistema unificado para o responsável."""
    try:
        from notifications.models import Notificacao

        if not doc.responsavel:
            return

        if tipo == 'vencido':
            titulo = f"Documento vencido: {doc.nome}"
            mensagem = f"O documento '{doc.nome}' venceu em {doc.data_vencimento.strftime('%d/%m/%Y')}."
            prioridade = 'alta'
            icone = 'bi-file-earmark-x'
        else:
            dias = (doc.data_vencimento - timezone.now().date()).days
            titulo = f"Documento a vencer: {doc.nome}"
            mensagem = f"O documento '{doc.nome}' vence em {dias} dias ({doc.data_vencimento.strftime('%d/%m/%Y')})."
            prioridade = 'media'
            icone = 'bi-file-earmark-excel'

        # Evita notificação duplicada no mesmo dia
        ja_notificado = Notificacao.objects.filter(
            usuario=doc.responsavel,
            titulo=titulo,
            criado_em__date=timezone.now().date(),
        ).exists()

        if not ja_notificado:
            Notificacao.objects.create(
                usuario=doc.responsavel,
                titulo=titulo,
                mensagem=mensagem,
                categoria='documento',
                prioridade=prioridade,
                icone=icone,
                url_destino=reverse_lazy_safe('documentos:lista'),
            )
    except ImportError:
        logger.debug("[Documentos] App notifications não disponível.")
    except Exception as e:
        logger.warning(f"[Documentos] Erro ao criar notificação: {e}")


def reverse_lazy_safe(url_name):
    """Resolve URL sem quebrar se não existir."""
    try:
        from django.urls import reverse
        return reverse(url_name)
    except Exception:
        return '/documentos/'

