
from django import template
from core.utils import mascarar_cpf

register = template.Library()


def _somente_digitos(valor):
    return ''.join(filter(str.isdigit, valor or ''))


def _mascarar_generico(numero, manter_final=4, manter_inicio=0):
    """Mascara mantendo apenas os últimos N caracteres visíveis."""
    if not numero:
        return numero
    if len(numero) <= manter_final:
        return '*' * len(numero)
    inicio = numero[:manter_inicio] if manter_inicio else ''
    return f"{inicio}{'*' * (len(numero) - manter_inicio - manter_final)}{numero[-manter_final:]}"


@register.filter
def mascarar_documento(numero, tipo):
    """
    Mascara o número do documento conforme o tipo.
    Uso: {{ doc.numero|mascarar_documento:doc.tipo_documento }}
    """
    if not numero:
        return numero

    numero = str(numero)
    digits = _somente_digitos(numero)

    # ── CPF ──────────────────────────────────────────────────────────
    if tipo == 'CPF':
        return mascarar_cpf(numero)

    # ── RG ───────────────────────────────────────────────────────────
    if tipo == 'RG':
        if len(digits) < 4:
            return numero
        return f"**.***.{digits[-3:]}"

    # ── CNH ──────────────────────────────────────────────────────────
    if tipo == 'CNH':
        return _mascarar_generico(digits, manter_final=3)

    # ── CTPS ─────────────────────────────────────────────────────────
    if tipo == 'CTPS':
        return _mascarar_generico(digits, manter_final=3)

    # ── PIS / PASEP / NIT ────────────────────────────────────────────
    if tipo == 'PIS':
        return _mascarar_generico(digits, manter_final=3)

    # ── Título de Eleitor ────────────────────────────────────────────
    if tipo == 'TITULO':
        return _mascarar_generico(digits, manter_final=3)

    # ── Certificado de Reservista ────────────────────────────────────
    if tipo == 'RESERVISTA':
        return _mascarar_generico(digits, manter_final=3)

    # ── Certidão de Nascimento / Casamento ───────────────────────────
    if tipo in ('CERTIDAO_NASC', 'CERTIDAO_CAS'):
        return _mascarar_generico(numero, manter_final=4)

    # ── Passaporte ───────────────────────────────────────────────────
    if tipo == 'PASSAPORTE':
        return _mascarar_generico(numero, manter_final=3)

    # ── RNE / CRNM ───────────────────────────────────────────────────
    if tipo == 'RNE':
        return _mascarar_generico(numero, manter_final=3)

    # ── Registro de Classe (CREA, CRM, OAB...) ───────────────────────
    if tipo == 'REGISTRO_CLASSE':
        return _mascarar_generico(numero, manter_final=4)

    # ── ASO — geralmente não tem "número" sensível, mas mascara mesmo ─
    if tipo == 'ASO':
        return _mascarar_generico(numero, manter_final=4)

    # ── NR (NR-10, NR-35...) — não é sensível, exibe completo ────────
    if tipo == 'NR':
        return numero

    # ── Comprovante de Endereço / Escolaridade — não sensível ────────
    if tipo in ('COMPROVANTE_END', 'COMP_ESCOLAR'):
        return numero

    # ── Certificado / Diploma — não sensível ─────────────────────────
    if tipo == 'CERTIFICADO':
        return numero

    # ── Outro — mascara por padrão (mais seguro) ─────────────────────
    if tipo == 'OUTRO':
        return _mascarar_generico(numero, manter_final=4)

    # ── Fallback: mascara genérico ────────────────────────────────────
    return _mascarar_generico(numero, manter_final=4)


