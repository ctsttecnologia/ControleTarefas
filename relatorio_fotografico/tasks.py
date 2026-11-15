import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.apps import apps
from django.utils import timezone

from relatorio_fotografico.services.analise_texto import analise_para_texto

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def preencher_endereco_foto(self, foto_id):
    """Busca o endereço via geocodificação e salva na foto."""
    from .services.geocoding import obter_endereco_por_coordenadas

    FotoRelatorio = apps.get_model('relatorio_fotografico', 'FotoRelatorio')

    try:
        foto = FotoRelatorio.objects.get(pk=foto_id)
    except FotoRelatorio.DoesNotExist:
        return

    if foto.endereco or not foto.tem_geolocalizacao:
        return

    try:
        endereco = obter_endereco_por_coordenadas(foto.latitude, foto.longitude)
    except Exception as exc:
        raise self.retry(exc=exc)

    if endereco:
        foto.endereco = endereco[:255]
        foto.save(update_fields=['endereco'])


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=15,
    soft_time_limit=240,   # não funciona com --pool=solo; timeout do SDK garante
    time_limit=300,
)
def analisar_relatorio_ia(self, analise_id):
    """Processa uma análise consolidada em segundo plano."""
    from .services.ia import ErroAnaliseIA, analisar_relatorio

    RelatorioVisao = apps.get_model('relatorio_fotografico', 'RelatorioVisao')

    atualizada = RelatorioVisao.objects.filter(
        pk=analise_id,
        status=RelatorioVisao.STATUS_AGUARDANDO,
    ).update(
        status=RelatorioVisao.STATUS_PROCESSANDO,
        iniciado_em=timezone.now(),
        erro='',
    )
    if not atualizada:  # evita execução duplicada
        return

    analise = RelatorioVisao.objects.select_related('relatorio').get(pk=analise_id)

    try:
        resultado = analisar_relatorio(analise.relatorio)

    except Exception as exc:
        if isinstance(exc, SoftTimeLimitExceeded):
            mensagem, retentavel = 'Tempo limite da tarefa excedido.', False
        elif isinstance(exc, ErroAnaliseIA):
            mensagem, retentavel = str(exc), exc.retentavel
        else:
            mensagem, retentavel = f'Erro inesperado: {exc}', False

        logger.exception('Falha na análise IA %s: %s', analise_id, mensagem)

        if retentavel and self.request.retries < self.max_retries:
            RelatorioVisao.objects.filter(pk=analise_id).update(
                status=RelatorioVisao.STATUS_AGUARDANDO,
                erro=f'Falha temporária ({mensagem}). Nova tentativa agendada.'[:4000],
            )
            raise self.retry(exc=exc)

        RelatorioVisao.objects.filter(pk=analise_id).update(
            status=RelatorioVisao.STATUS_ERRO,
            erro=mensagem[:4000],
            concluido_em=timezone.now(),
        )
        return

    analise.resultado = resultado
    analise.status = RelatorioVisao.STATUS_CONCLUIDO
    analise.erro = ''
    analise.concluido_em = timezone.now()
    analise.save(update_fields=['resultado', 'status', 'erro', 'concluido_em', 'updated_at'])
    analise.texto = analise_para_texto(analise.resultado)


    logger.info('Análise IA %s concluída para relatório %s', analise.pk, analise.relatorio_id)

