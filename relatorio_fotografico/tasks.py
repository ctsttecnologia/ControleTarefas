
# relatorio_fotografico/tasks.py
from celery import shared_task
from django.apps import apps


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def preencher_endereco_foto(self, foto_id):
    """Busca o endereço via geocodificação e salva na foto, sem travar o request."""
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
        # Tenta novamente em caso de falha temporária (timeout, rede, etc.)
        raise self.retry(exc=exc)

    if endereco:
        foto.endereco = endereco[:255]
        foto.save(update_fields=['endereco'])

