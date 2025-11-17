
# Em documentos/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Documento  # Importe seu modelo Documento

# (Opcional, mas recomendado) Configure um logger
logger = logging.getLogger(__name__)

# Defina seu "período de aviso" (ex: 30 dias)
DIAS_AVISO_PREVIO = 30

@shared_task(name="documentos.verificar_vencimentos")
def verificar_vencimentos_documentos():
    """
    Tarefa Celery para verificar diariamente os documentos
    a vencer e os vencidos.
    """
    hoje = timezone.now().date()
    data_limite_aviso = hoje + timedelta(days=DIAS_AVISO_PREVIO)

    logger.info(f"Iniciando verificação de vencimentos em {hoje}...")

    # 1. Documentos que VENCERAM
    # Filtra documentos que venceram antes de hoje E que ainda não estão 'VENCIDO'
    vencidos = Documento.objects.filter(
        data_vencimento__lt=hoje,
        status__in=[Documento.StatusChoices.VIGENTE, Documento.StatusChoices.A_VENCER]
    )
    
    count_vencidos = 0
    for doc in vencidos:
        doc.status = Documento.StatusChoices.VENCIDO
        doc.save(update_fields=['status'])
        
        # Lógica de Notificação (ex: django-notifications)
        # notificator.send(doc.responsavel, verb=f"O documento '{doc.nome}' venceu!")
        count_vencidos += 1

    if count_vencidos > 0:
        logger.warning(f"{count_vencidos} documentos atualizados para VENCIDO.")

    # 2. Documentos que ESTÃO "A VENCER"
    # Filtra docs que vencem entre hoje e a data limite E que ainda estão 'VIGENTE'
    a_vencer = Documento.objects.filter(
        data_vencimento__gte=hoje,
        data_vencimento__lte=data_limite_aviso,
        status=Documento.StatusChoices.VIGENTE
    )
    
    count_a_vencer = 0
    for doc in a_vencer:
        doc.status = Documento.StatusChoices.A_VENCER
        doc.save(update_fields=['status'])
        
        # Lógica de Notificação (Aviso)
        # notificator.send(doc.responsavel, verb=f"AVISO: O documento '{doc.nome}' vencerá em {doc.data_vencimento}!")
        count_a_vencer += 1
        
    if count_a_vencer > 0:
        logger.info(f"{count_a_vencer} documentos atualizados para A VENCER.")

    logger.info("Verificação de vencimentos concluída.")
    return f"Concluído: {count_vencidos} vencidos, {count_a_vencer} a vencer."
