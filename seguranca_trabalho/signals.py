
from django.db.models import F, Sum, Q
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import MovimentacaoEstoque, Equipamento


def recalcular_estoque(equipamento_id, filial_id=None):
    """
    Recalcula o estoque de um equipamento a partir do zero,
    com base em todas as movimentações registradas.

    Use apenas para reconciliação manual (ex.: management command),
    pois é uma operação custosa. O fluxo normal usa atualização
    incremental via signals.
    """
    qs = MovimentacaoEstoque.objects.filter(equipamento_id=equipamento_id)
    if filial_id is not None:
        qs = qs.filter(filial_id=filial_id)

    resultado = qs.aggregate(
        total_entradas=Sum('quantidade', filter=Q(tipo='ENTRADA'), default=0),
        total_saidas=Sum('quantidade', filter=Q(tipo='SAIDA'), default=0),
    )
    estoque = (resultado['total_entradas'] or 0) - (resultado['total_saidas'] or 0)

    equipamento_qs = Equipamento.objects.filter(pk=equipamento_id)
    if filial_id is not None:
        equipamento_qs = equipamento_qs.filter(filial_id=filial_id)

    equipamento_qs.update(estoque_atual=estoque)


@receiver(post_save, sender=MovimentacaoEstoque)
def atualizar_estoque_on_save(sender, instance, created, **kwargs):
    """
    Atualiza o estoque incrementalmente após uma movimentação ser criada.

    Em updates (created=False), o ideal é proibir alteração de quantidade/tipo
    no clean() do model, ou então usar recalcular_estoque() para garantir
    consistência. Aqui assumimos que movimentações são imutáveis após criação.
    """
    if not created:
        # Movimentações devem ser imutáveis; se houver edição, recalcula tudo
        # para evitar inconsistências.
        recalcular_estoque(instance.equipamento_id, instance.filial_id)
        return

    Equipamento.objects.filter(pk=instance.equipamento_id).update(
        estoque_atual=F('estoque_atual') + instance.delta
    )


@receiver(post_delete, sender=MovimentacaoEstoque)
def atualizar_estoque_on_delete(sender, instance, **kwargs):
    """Reverte o impacto no estoque quando uma movimentação é excluída."""
    Equipamento.objects.filter(pk=instance.equipamento_id).update(
        estoque_atual=F('estoque_atual') - instance.delta
    )


