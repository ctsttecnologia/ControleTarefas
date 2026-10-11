# pgr_gestao/signals.py
import logging
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from pgr_gestao.models import AnexoPGR, AnexoPlanoAcao
from pgr_gestao.services import risco as risco_svc
from pgr_gestao.services.cronograma import criar_cronograma_padrao
from pgr_gestao.services.notificacoes import enviar
from pgr_gestao.services.plano_acao import criar_plano_automatico
from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)
GRAVES = ("critico", "muito_grave")


@receiver(post_delete, sender=AnexoPGR)
@receiver(post_delete, sender=AnexoPlanoAcao)
def apagar_arquivo(sender, instance, **kw):
    f = getattr(instance, "arquivo", None)
    if f:
        transaction.on_commit(lambda: f.storage.delete(f.name))

@receiver(pre_save, sender="pgr_gestao.PGRDocumento")
def verificar_vencimento_pgr(sender, instance, **kw):
    if not instance.pk or not instance.data_vencimento:
        return
    hoje = timezone.localdate()
    if instance.data_vencimento < hoje and instance.status == "vigente":
        instance.status = "vencido"
    elif instance.data_vencimento >= hoje and instance.status == "vencido":
        instance.status = "vigente"


@receiver(post_save, sender="pgr_gestao.PGRDocumento")
def pgr_criado(sender, instance, created, **kw):
    if not created:
        return
    criar_cronograma_padrao(instance)
    logger.info("PGR criado id=%s código=%s", instance.pk, instance.codigo_documento)
    transaction.on_commit(lambda: enviar(
        "EMAIL_NOTIFICACAO_PGR",
        f"Novo PGR criado: {instance.codigo_documento}",
        f"Código: {instance.codigo_documento}\n"
        f"Vencimento: {instance.data_vencimento:%d/%m/%Y}",
    ))


@receiver(post_save, sender="pgr_gestao.PGRRevisao")
def atualizar_versao_pgr(sender, instance, created, **kw):
    if created:  # a view NÃO deve repetir esta lógica
        pgr = instance.pgr_documento
        pgr.versao_atual = instance.numero_revisao + 1
        pgr.data_ultima_revisao = instance.data_realizacao
        pgr.save(update_fields=["versao_atual", "data_ultima_revisao"])


@receiver(pre_save, sender="pgr_gestao.RiscoIdentificado")
def classificar_risco(sender, instance, **kw):
    risco_svc.aplicar_classificacao(instance)


@receiver(post_save, sender="pgr_gestao.RiscoIdentificado")
def risco_grave(sender, instance, created, **kw):
    if not (created and instance.classificacao_risco in GRAVES):
        return
    criar_plano_automatico(instance)
    logger.warning("Risco %s identificado id=%s pgr=%s",
                   instance.classificacao_risco, instance.pk, instance.pgr_documento_id)
    transaction.on_commit(lambda: enviar(
        "EMAIL_ALERTA_RISCO_CRITICO",
        f"ALERTA: risco {instance.get_classificacao_risco_display()} identificado",
        f"Risco id={instance.pk} (PGR {instance.pgr_documento.codigo_documento}). "
        "Acesse o sistema para tratar.",  # sem agente/efeitos à saúde no e-mail
    ))


@receiver(pre_save, sender="pgr_gestao.PlanoAcaoPGR")
def status_plano(sender, instance, **kw):
    if not instance.pk:
        return
    if instance.status == "concluido" and not instance.data_conclusao:
        instance.data_conclusao = timezone.localdate()
    elif instance.status in ("pendente", "em_andamento"):
        instance.data_conclusao = None


@receiver(post_save, sender="pgr_gestao.PlanoAcaoPGR")
def risco_controlado(sender, instance, created, **kw):
    if created or instance.status != "concluido":
        return
    risco = instance.risco_identificado
    if not risco.planos_acao.exclude(status="concluido").exists():
        risco.status_controle = "controlado"
        risco.save(update_fields=["status_controle"])


@receiver(post_save, sender="pgr_gestao.AvaliacaoQuantitativa")
def avaliacao_salva(sender, instance, created, **kw):
    risco = instance.risco_identificado
    if created and risco.metodo_avaliacao != "quantitativo":
        risco.metodo_avaliacao = "quantitativo"
        risco.save(update_fields=["metodo_avaliacao"])
    if instance.conforme is False:
        logger.warning("Avaliação NÃO CONFORME id=%s risco=%s", instance.pk, risco.pk)

