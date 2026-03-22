
# suprimentos/signals.py

from decimal import Decimal
import logging

from django.db.models import F
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import ItemPedido, Pedido, EstoqueConsumo, CategoriaMaterial

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Pedido)
def pedido_recebido_gerar_entrada_estoque(sender, instance, **kwargs):
    """
    Quando um pedido muda para RECEBIDO, gera entrada automática no estoque:
    - EPI       → MovimentacaoEstoque (seguranca_trabalho)
    - CONSUMO   → EstoqueConsumo (suprimentos)
    - FERRAMENTA → Ferramenta.quantidade (ferramentas)

    A flag `estoque_processado` evita dupla entrada.
    """
    # Só processa pedidos já existentes
    if not instance.pk:
        return

    # Já processou estoque? Não faz de novo
    if instance.estoque_processado:
        return

    # Busca status anterior no banco
    try:
        pedido_anterior = Pedido.objects.only('status', 'estoque_processado').get(pk=instance.pk)
    except Pedido.DoesNotExist:
        return

    # Só processa na transição ENTREGUE → RECEBIDO
    if (pedido_anterior.status != Pedido.StatusChoices.ENTREGUE
            or instance.status != Pedido.StatusChoices.RECEBIDO):
        return

    logger.info(
        f"📦 Pedido {instance.numero} RECEBIDO — gerando entrada no estoque..."
    )

    itens = instance.itens.select_related(
        'material',
        'material__equipamento_epi',
        'material__ferramenta_ref',
    ).all()

    filial = instance.contrato.filial
    responsavel_id = instance.recebedor_id or instance.solicitante_id
    entradas_ok = 0
    entradas_erro = 0

    for item in itens:
        material = item.material
        classificacao = material.classificacao

        try:
            if classificacao == CategoriaMaterial.EPI:
                _entrada_epi(item, material, filial, instance, responsavel_id)
                entradas_ok += 1

            elif classificacao == CategoriaMaterial.CONSUMO:
                _entrada_consumo(item, material, filial, instance, responsavel_id)
                entradas_ok += 1

            elif classificacao == CategoriaMaterial.FERRAMENTA:
                _entrada_ferramenta(item, material, filial, instance)
                entradas_ok += 1
            # ═══ NOVO: Recalcular tributação ao receber ═══
            if material.grupo_tributario and item.custo_real == Decimal('0.00'):
                calc = item.calcular_impostos()
                ItemPedido.objects.filter(pk=item.pk).update(
                    custo_real=calc['custo_real'],
                    total_creditos=calc['total_creditos'],
                    total_impostos=calc['total_impostos'],
                )
                logger.info(
                    f"  💰 Tributação: {material.descricao} — "
                    f"Custo real R$ {calc['custo_real']} "
                    f"(créditos R$ {calc['total_creditos']})"
                )


        except Exception as e:
            entradas_erro += 1
            logger.error(
                f"  ❌ Erro ao dar entrada do item '{material.descricao}' "
                f"(pedido {instance.numero}): {e}"
            )

    # Marca como processado para evitar dupla entrada
    instance.estoque_processado = True

    logger.info(
        f"  📊 Resumo pedido {instance.numero}: "
        f"{entradas_ok} entradas OK, {entradas_erro} erros"
    )


def _entrada_epi(item, material, filial, pedido, responsavel_id):
    """Dá entrada no estoque de EPI via MovimentacaoEstoque (SST)."""
    from seguranca_trabalho.models import MovimentacaoEstoque

    equipamento = material.equipamento_epi
    if not equipamento:
        logger.warning(
            f"  ⚠️ Material EPI '{material.descricao}' (cód. {material.codigo}) "
            f"sem vínculo com Equipamento SST. Entrada NÃO realizada. "
            f"Vincule em Catálogo > Materiais > Editar."
        )
        return

    MovimentacaoEstoque.objects.create(
        equipamento=equipamento,
        tipo='ENTRADA',
        quantidade=item.quantidade,
        custo_unitario=item.valor_unitario,
        responsavel_id=responsavel_id,
        justificativa=f"Entrada automática — Pedido {pedido.numero}",
        filial=filial,
        data=timezone.now(),
    )
    logger.info(
        f"  ✅ EPI: +{item.quantidade} '{equipamento.nome}' "
        f"(Equipamento #{equipamento.pk})"
    )


def _entrada_consumo(item, material, filial, pedido, responsavel_id):
    """Dá entrada no EstoqueConsumo (suprimentos)."""
    EstoqueConsumo.objects.create(
        material=material,
        contrato=pedido.contrato,
        tipo=EstoqueConsumo.TipoMovimento.ENTRADA,
        quantidade=item.quantidade,
        pedido=pedido,
        responsavel_id=responsavel_id,
        justificativa=f"Entrada automática — Pedido {pedido.numero}",
        filial=filial,
    )
    logger.info(
        f"  ✅ CONSUMO: +{item.quantidade} '{material.descricao}' "
        f"(Contrato {pedido.contrato.cm})"
    )


def _entrada_ferramenta(item, material, filial, pedido):
    """Incrementa quantidade da Ferramenta vinculada."""
    from ferramentas.models import Ferramenta

    ferramenta = material.ferramenta_ref
    if not ferramenta:
        logger.warning(
            f"  ⚠️ Material FERRAMENTA '{material.descricao}' (cód. {material.codigo}) "
            f"sem vínculo com Ferramenta. Entrada NÃO realizada. "
            f"Vincule em Catálogo > Materiais > Editar."
        )
        return

    Ferramenta.objects.filter(pk=ferramenta.pk).update(
        quantidade=F('quantidade') + item.quantidade
    )
    logger.info(
        f"  ✅ FERRAMENTA: +{item.quantidade} '{ferramenta.nome}' "
        f"(Ferramenta #{ferramenta.pk})"
    )
