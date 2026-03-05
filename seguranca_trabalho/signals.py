
from django.db import models as db_models
from django.db.models import Sum, Q
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import MovimentacaoEstoque, Equipamento


def recalcular_estoque(equipamento_id, filial_id):
    """Recalcula o estoque de um equipamento com base nas movimentações."""
    resultado = MovimentacaoEstoque.objects.filter(
        equipamento_id=equipamento_id,
        filial_id=filial_id,
    ).aggregate(
        total_entradas=Sum('quantidade', filter=Q(tipo='ENTRADA'), default=0),
        total_saidas=Sum('quantidade', filter=Q(tipo='SAIDA'), default=0),
    )
    estoque = resultado['total_entradas'] - resultado['total_saidas']
    Equipamento.objects.filter(
        pk=equipamento_id, filial_id=filial_id
    ).update(estoque_atual=estoque)


@receiver(post_save, sender=MovimentacaoEstoque)
def atualizar_estoque_on_save(sender, instance, **kwargs):
    recalcular_estoque(instance.equipamento_id, instance.filial_id)


@receiver(post_delete, sender=MovimentacaoEstoque)
def atualizar_estoque_on_delete(sender, instance, **kwargs):
    recalcular_estoque(instance.equipamento_id, instance.filial_id)

