
# helpers.py
import re
import base64 as b64lib
from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError
from py_serializable import logger

from treinamentos.views import mark_safe


BASE64_RE = re.compile(r'^[A-Za-z0-9+/]+={0,2}$')
MAX_SIG_LENGTH = 500_000  # ~375KB

def _processar_assinatura_base64(sig_str):
    """Valida e normaliza assinatura base64. Retorna None se inválida/suspeita."""
    if not sig_str:
        return None
    sig = sig_str.strip()
    if len(sig) > MAX_SIG_LENGTH:
        logger.warning("Assinatura rejeitada: excede tamanho máximo (%d bytes).", len(sig))
        return None

    if sig.startswith('data:image'):
        try:
            header, payload = sig.split(',', 1)
        except ValueError:
            return None
        if not (header.startswith('data:image/png;base64')
                or header.startswith('data:image/jpeg;base64')):
            return None
        if not BASE64_RE.match(payload):
            return None
        try:
            b64lib.b64decode(payload, validate=True)
        except Exception:
            return None
        return mark_safe(sig)

    if len(sig) > 100 and BASE64_RE.match(sig):
        try:
            b64lib.b64decode(sig, validate=True)
        except Exception:
            return None
        return mark_safe(f'data:image/png;base64,{sig}')

    return None

def registrar_movimentacao_estoque(
    equipamento, tipo, quantidade, responsavel, justificativa,
    filial=None, entrega_associada=None,
):
    """
    Registra uma movimentação de estoque e atualiza `estoque_atual` do
    equipamento de forma atômica e segura contra concorrência.

    - Usa select_for_update() para travar a linha do equipamento durante
      toda a transação, serializando requisições simultâneas.
    - Usa F() expressions para o incremento/decremento, evitando problemas
      de "leitura suja" entre o SELECT e o UPDATE.
    - A validação final de estoque negativo é feita após o lock, com o
      dado mais atualizado possível; a CheckConstraint no banco é a
      última linha de defesa caso algo escape da lógica da aplicação.

    Levanta ValidationError se a saída deixaria o estoque negativo.
    """
    from .models import Equipamento, MovimentacaoEstoque

    filial = filial or equipamento.filial

    with transaction.atomic():
        # Trava a linha do equipamento — qualquer outra chamada concorrente
        # para o MESMO equipamento aguarda até esta transação concluir.
        equipamento_travado = (
            Equipamento.objects.select_for_update().get(pk=equipamento.pk)
        )

        if tipo == 'SAIDA' and quantidade > equipamento_travado.estoque_atual:
            raise ValidationError(
                f"Estoque insuficiente para '{equipamento_travado.nome}'. "
                f"Disponível: {equipamento_travado.estoque_atual}, "
                f"solicitado: {quantidade}."
            )

        movimentacao = MovimentacaoEstoque.objects.create(
            equipamento=equipamento_travado,
            tipo=tipo,
            quantidade=quantidade,
            justificativa=justificativa,
            responsavel=responsavel,
            filial=filial,
            entrega_associada=entrega_associada,
        )

        # Atualização atômica via F() — o próprio banco executa
        # "estoque_atual = estoque_atual + N" em uma única instrução SQL,
        # sem race condition entre leitura e escrita em Python.
        delta = quantidade if tipo == 'ENTRADA' else -quantidade
        Equipamento.objects.filter(pk=equipamento_travado.pk).update(
            estoque_atual=F('estoque_atual') + delta
        )

        return movimentacao