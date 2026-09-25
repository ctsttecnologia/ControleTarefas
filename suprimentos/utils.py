
# suprimentos/utils.py
import logging

import re
from django.core.exceptions import ValidationError

CNPJ_FORMATO_REGEX = re.compile(r'^[0-9A-Z]{2}\.[0-9A-Z]{3}\.[0-9A-Z]{3}/[0-9A-Z]{4}-\d{2}$')

PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
PESOS_DV2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


logger = logging.getLogger(__name__)


def _registrar_historico(func, **kwargs):
    """Wrapper seguro para registro de histórico — nunca quebra o fluxo."""
    try:
        func(**kwargs)
    except Exception:
        logger.exception("Falha ao registrar histórico (%s)", func.__qualname__)

# Validdaor CNPJ

def _valor_caractere(char):
    """Converte caractere (dígito ou letra) para valor numérico: ASCII - 48."""
    return ord(char) - 48


def _calcular_dv(base, pesos):
    soma = sum(_valor_caractere(c) * p for c, p in zip(base, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def validar_cnpj(cnpj):
    """
    Valida CNPJ (numérico ou alfanumérico) com máscara.
    Levanta ValidationError se inválido. Retorna o CNPJ normalizado (upper) se válido.
    """
    if not cnpj:
        return None

    # Aceita int/float vindos de células Excel sem formatação de texto
    if isinstance(cnpj, (int, float)):
        cnpj = str(int(cnpj)).zfill(14)
        cnpj = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    else:
        cnpj = str(cnpj)

    cnpj = cnpj.strip().upper()

    if not CNPJ_FORMATO_REGEX.match(cnpj):
        raise ValidationError(
            "CNPJ inválido. Use o formato 00.000.000/0000-00 "
            "(aceita letras nas 12 primeiras posições, conforme padrão vigente desde jul/2026)."
        )

    limpo = re.sub(r'[.\-/]', '', cnpj)  # remove pontuação -> 14 caracteres

    if len(limpo) != 14:
        raise ValidationError("CNPJ deve conter 14 caracteres (sem contar a pontuação).")

    base12 = limpo[:12]
    dv_informado = limpo[12:]

    if not dv_informado.isdigit():
        raise ValidationError("Os dois últimos dígitos verificadores devem ser numéricos.")

    dv1 = _calcular_dv(base12, PESOS_DV1)
    dv2 = _calcular_dv(base12 + str(dv1), PESOS_DV2)

    if dv_informado != f"{dv1}{dv2}":
        raise ValidationError("CNPJ inválido: dígito verificador não corresponde.")

    return cnpj
