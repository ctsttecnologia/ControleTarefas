
# pgr_gestao/unidades.py
from pgr_gestao.models import TIPO_AVALIACAO_CHOICES, UNIDADE_MEDIDA_CHOICES

# Tipo "outro" fica sem mapeamento de propósito: mostra todas as unidades.
UNIDADES_POR_TIPO: dict[str, list[str]] = {
    "ruido": ["dB", "dB(A)", "%", "outro"],            # % = dose de ruído
    "calor": ["IBUTG", "ºC", "UR", "m/s", "outro"],    # temperatura, umidade, vel. do ar
    "iluminacao": ["lux", "outro"],
    "agente_quimico": ["ppm", "mg/m³", "f/cm³", "%", "outro"],
    "vibracao": ["m/s²", "outro"],
    "radiacao": ["mW/cm²", "Bq", "mSv", "outro"],
}

_TODAS = list(UNIDADE_MEDIDA_CHOICES)


def choices_para(tipo):
    """Unidades permitidas para o tipo; sem mapeamento, retorna todas."""
    permitidas = UNIDADES_POR_TIPO.get(tipo)
    if not permitidas:
        return _TODAS
    return [c for c in _TODAS if c[0] in permitidas]


def mapa_para_js():
    """{tipo: [[valor, rótulo], ...]} para o filtro dinâmico no front."""
    return {t: [list(c) for c in choices_para(t)] for t, _ in TIPO_AVALIACAO_CHOICES}


def tipo_do_form(form):
    """Tipo vindo do POST, da instância ou do initial."""
    if form.is_bound:
        return form.data.get(form.add_prefix("tipo_avaliacao"))
    return getattr(form.instance, "tipo_avaliacao", None) or form.initial.get("tipo_avaliacao")

