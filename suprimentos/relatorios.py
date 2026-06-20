# suprimentos/relatorios.py
"""
Módulo de relatórios gerenciais do Suprimentos (REFATORADO).

Estratégia de performance:
  - Substitui loops aninhados (N+1) por agregações em lote com
    values().annotate(), construindo "mapas" em memória.
  - Reduz de centenas/milhares de queries para um número FIXO (~12).
  - Suporta períodos que cruzam anos.
  - Tipagem Decimal consistente com .quantize() na saída.
"""

import logging
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from django.db.models import Sum, Count, DecimalField, IntegerField, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.db.models import Sum

from .models import Contrato, Pedido, VerbaContrato, ItemPedido, CategoriaMaterial

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────

ZERO = Decimal("0.00")
DEC = DecimalField(max_digits=18, decimal_places=2)
INT = IntegerField()
CENTAVO = Decimal("0.01")

STATUS_COMPRA = ["APROVADO", "ENTREGUE", "RECEBIDO"]

# Ordem fixa de categorias (cod, label)
CATEGORIAS = [
    (CategoriaMaterial.EPI, "EPI"),
    (CategoriaMaterial.CONSUMO, "Consumo"),
    (CategoriaMaterial.FERRAMENTA, "Ferramenta"),
]
CODS = [c for c, _ in CATEGORIAS]

# Mapeia categoria -> campo de verba correspondente
VERBA_FIELD = {
    CategoriaMaterial.EPI: "verba_epi",
    CategoriaMaterial.CONSUMO: "verba_consumo",
    CategoriaMaterial.FERRAMENTA: "verba_ferramenta",
}

_NOMES_MES = [
    "", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]

# Status considerados "efetivados" no relatório
STATUS_VALIDOS = [
    Pedido.StatusChoices.APROVADO,
    Pedido.StatusChoices.ENTREGUE,
    Pedido.StatusChoices.RECEBIDO,
    Pedido.StatusChoices.SOLICITACAO_GERADA,
]


# ─────────────────────────────────────────────────────────────
# HELPERS BÁSICOS
# ─────────────────────────────────────────────────────────────

def _D(v) -> Decimal:
    """Converte qualquer valor para Decimal seguro."""
    if v is None:
        return ZERO
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _q(v) -> Decimal:
    """Quantiza para 2 casas (saída)."""
    return _D(v).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _label_mes(ano, mes) -> str:
    return f"{_NOMES_MES[mes]}/{ano}"


def _meses_periodo(ano_ini, mes_ini, ano_fim, mes_fim):
    """Lista de (ano, mes) entre dois períodos, inclusive. Suporta multi-ano."""
    meses = []
    a, m = ano_ini, mes_ini
    # trava de segurança: máx 120 meses (10 anos)
    for _ in range(120):
        if (a, m) > (ano_fim, mes_fim):
            break
        meses.append((a, m))
        m += 1
        if m > 12:
            m, a = 1, a + 1
    return meses


def _pct(parte, total) -> Decimal:
    parte, total = _D(parte), _D(total)
    if total == ZERO:
        return ZERO
    return ((parte / total) * 100).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _variacao_pct(atual, anterior) -> Decimal:
    atual, anterior = _D(atual), _D(anterior)
    if anterior == ZERO:
        return Decimal("100.00") if atual > ZERO else ZERO
    return (((atual - anterior) / anterior) * 100).quantize(
        CENTAVO, rounding=ROUND_HALF_UP
    )


# ─────────────────────────────────────────────────────────────
# VALIDAÇÃO E NORMALIZAÇÃO DE PARÂMETROS
# ─────────────────────────────────────────────────────────────

def _normalizar_periodo(ano_ini, mes_ini, ano_fim=None, mes_fim=None):
    """Valida e normaliza um período. Levanta ValueError se inválido."""
    ano_fim = ano_fim if ano_fim is not None else ano_ini
    mes_fim = mes_fim if mes_fim is not None else mes_ini

    for nome, mes in (("mes_ini", mes_ini), ("mes_fim", mes_fim)):
        if not (1 <= int(mes) <= 12):
            raise ValueError(f"{nome} inválido: {mes} (esperado 1..12)")

    if (ano_ini, mes_ini) > (ano_fim, mes_fim):
        raise ValueError("Período inicial não pode ser maior que o final.")

    return int(ano_ini), int(mes_ini), int(ano_fim), int(mes_fim)


def _normalizar_contratos(contrato_ids):
    """Remove duplicados e valores falsy, garante lista de ints."""
    return sorted({int(c) for c in (contrato_ids or []) if c})


# ─────────────────────────────────────────────────────────────
# MAPAS EM LOTE (núcleo da performance)
# ─────────────────────────────────────────────────────────────

def _filtro_itens(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim):
    """
    Filtro de ItemPedido por período multi-ano.
    Usa data_pedido (DateTimeField). Para multi-ano, filtramos por
    intervalo de datas no nível de mês.
    """
    from django.db.models import Q

    di = date(ano_ini, mes_ini, 1)
    # primeiro dia do mês seguinte ao fim
    if mes_fim == 12:
        df = date(ano_fim + 1, 1, 1)
    else:
        df = date(ano_fim, mes_fim + 1, 1)

    return Q(
        pedido__contrato_id__in=contrato_ids,
        pedido__status__in=STATUS_COMPRA,
        pedido__data_pedido__date__gte=di,
        pedido__data_pedido__date__lt=df,
    )


def _mapa_gasto(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim):
    """
    1 QUERY → mapa[(contrato_id, ano, mes, categoria)] = {'valor':.., 'qtd':..}
    """
    qs = (
        ItemPedido.objects
        .filter(_filtro_itens(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim))
        .values(
            "pedido__contrato_id",
            "pedido__data_pedido__year",
            "pedido__data_pedido__month",
            "material__classificacao",
        )
        .annotate(
            valor=Coalesce(Sum("valor_total"), Value(ZERO), output_field=DEC),
            qtd=Coalesce(Sum("quantidade"), Value(0), output_field=INT),
            n_itens=Count("id"),
            n_pedidos=Count("pedido", distinct=True),
        )
    )
    mapa = {}
    for r in qs:
        chave = (
            r["pedido__contrato_id"],
            r["pedido__data_pedido__year"],
            r["pedido__data_pedido__month"],
            r["material__classificacao"],
        )
        mapa[chave] = {
            "valor": _D(r["valor"]),
            "qtd": int(r["qtd"] or 0),
            "n_itens": r["n_itens"],
            "n_pedidos": r["n_pedidos"],
        }
    return mapa


def _mapa_verba(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim):
    """
    1 QUERY → mapa[(contrato_id, ano, mes, categoria)] = Decimal(verba)
    """
    from django.db.models import Q

    # Filtro multi-ano por (ano, mes)
    filtro = Q()
    for a, m in _meses_periodo(ano_ini, mes_ini, ano_fim, mes_fim):
        filtro |= Q(ano=a, mes=m)
    if not filtro:
        return {}

    qs = (
        VerbaContrato.objects
        .filter(filtro, contrato_id__in=contrato_ids)
        .values("contrato_id", "ano", "mes")
        .annotate(
            epi=Coalesce(Sum("verba_epi"), Value(ZERO), output_field=DEC),
            consumo=Coalesce(Sum("verba_consumo"), Value(ZERO), output_field=DEC),
            ferramenta=Coalesce(Sum("verba_ferramenta"), Value(ZERO), output_field=DEC),
        )
    )
    mapa = {}
    for r in qs:
        base = (r["contrato_id"], r["ano"], r["mes"])
        mapa[(*base, CategoriaMaterial.EPI)] = _D(r["epi"])
        mapa[(*base, CategoriaMaterial.CONSUMO)] = _D(r["consumo"])
        mapa[(*base, CategoriaMaterial.FERRAMENTA)] = _D(r["ferramenta"])
    return mapa


def _g(mapa_gasto, cid, ano, mes, cod):
    """Acesso seguro ao gasto."""
    return mapa_gasto.get((cid, ano, mes, cod), {}).get("valor", ZERO)


def _v(mapa_verba, cid, ano, mes, cod):
    """Acesso seguro à verba."""
    return mapa_verba.get((cid, ano, mes, cod), ZERO)


# ═════════════════════════════════════════════════════════════
# 1. QUANTITATIVO
# ═════════════════════════════════════════════════════════════

def relatorio_quantitativo(contrato_ids, ano, mes_ini, mes_fim, ano_fim=None):
    contrato_ids = _normalizar_contratos(contrato_ids)
    ano_ini, mes_ini, ano_fim, mes_fim = _normalizar_periodo(
        ano, mes_ini, ano_fim, mes_fim
    )
    if not contrato_ids:
        return _quantitativo_vazio()

    meses = _meses_periodo(ano_ini, mes_ini, ano_fim, mes_fim)
    mapa = _mapa_gasto(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim)

    # ── Resumo geral por categoria (agrega o mapa) ──
    acc = {cod: {"valor": ZERO, "qtd": 0, "n_itens": 0, "pedidos": set()}
           for cod in CODS}
    for (cid, a, m, cod), v in mapa.items():
        if cod in acc:
            acc[cod]["valor"] += v["valor"]
            acc[cod]["qtd"] += v["qtd"]
            acc[cod]["n_itens"] += v["n_itens"]
            acc[cod]["pedidos"].add((cid, a, m))

    resumo_geral = []
    for cod, label in CATEGORIAS:
        d = acc[cod]
        resumo_geral.append({
            "categoria": cod,
            "categoria_label": label,
            "qtd_itens_linha": d["n_itens"],
            "qtd_unidades": d["qtd"],
            "valor_total": _q(d["valor"]),
        })
    total_geral = sum((r["valor_total"] for r in resumo_geral), ZERO)
    for r in resumo_geral:
        r["pct_valor"] = _pct(r["valor_total"], total_geral)

    # ── Por mês ──
    por_mes = []
    for a, m in meses:
        d = {"label": _label_mes(a, m), "ano": a, "mes": m}
        total_mes = ZERO
        for cod, _label in CATEGORIAS:
            val = ZERO
            qtd = 0
            for cid in contrato_ids:
                cell = mapa.get((cid, a, m, cod))
                if cell:
                    val += cell["valor"]
                    qtd += cell["qtd"]
            d[f"valor_{cod.lower()}"] = _q(val)
            d[f"qtd_{cod.lower()}"] = qtd
            total_mes += val
        d["valor_total"] = _q(total_mes)
        por_mes.append(d)

    # ── Top materiais (1 QUERY dedicada) ──
    top_materiais = list(
        ItemPedido.objects
        .filter(_filtro_itens(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim))
        .values("material__descricao", "material__classificacao", "material__unidade")
        .annotate(
            qtd_total=Coalesce(Sum("quantidade"), Value(0), output_field=INT),
            valor_total=Coalesce(Sum("valor_total"), Value(ZERO), output_field=DEC),
            vezes_pedido=Count("pedido", distinct=True),
        )
        .order_by("-valor_total")[:15]
    )

    # ── Por contrato ──
    contratos = {c.id: c for c in Contrato.objects.filter(id__in=contrato_ids)}
    por_contrato = []
    for cid in contrato_ids:
        ct = contratos.get(cid)
        if not ct:
            continue
        d = {"contrato": f"{ct.cm} — {ct.cliente}", "contrato_id": cid}
        total_ct = ZERO
        for cod, _label in CATEGORIAS:
            val = ZERO
            qtd = 0
            for a, m in meses:
                cell = mapa.get((cid, a, m, cod))
                if cell:
                    val += cell["valor"]
                    qtd += cell["qtd"]
            d[f"valor_{cod.lower()}"] = _q(val)
            d[f"qtd_{cod.lower()}"] = qtd
            total_ct += val
        d["valor_total"] = _q(total_ct)
        if total_ct > 0:
            por_contrato.append(d)
    por_contrato.sort(key=lambda x: x["valor_total"], reverse=True)

    return {
        "resumo_geral": resumo_geral,
        "total_geral_valor": _q(total_geral),
        "por_mes": por_mes,
        "top_materiais": top_materiais,
        "por_contrato": por_contrato,
    }


def _quantitativo_vazio():
    return {
        "resumo_geral": [
            {"categoria": c, "categoria_label": l, "qtd_itens_linha": 0,
             "qtd_unidades": 0, "valor_total": ZERO, "pct_valor": ZERO}
            for c, l in CATEGORIAS
        ],
        "total_geral_valor": ZERO,
        "por_mes": [], "top_materiais": [], "por_contrato": [],
    }

def total_periodo(contrato, inicio, fim):
    """
    Soma o valor_total dos itens de pedidos efetivados de um contrato,
    dentro do intervalo [inicio, fim].

    Usa ItemPedido.objects (manager padrão, sem FilialManager) para
    funcionar tanto em produção quanto em testes sem request ativo.
    """
    total = (
        ItemPedido.objects.filter(
            pedido__contrato=contrato,
            pedido__status__in=STATUS_VALIDOS,
            pedido__data_pedido__date__gte=inicio,
            pedido__data_pedido__date__lte=fim,
        )
        .aggregate(t=Sum("valor_total"))["t"]
    )
    return total or Decimal("0.00")

def total_por_tipo(contrato, inicio, fim):
    """
    Agrupa o valor_total por `material.tipo` (CIVIL, ELETRICA, EPI...).
    Retorna dict {tipo: Decimal}. Tipos sem movimento não aparecem.
    """
    qs = (
        ItemPedido.objects.filter(
            pedido__contrato=contrato,
            pedido__status__in=STATUS_VALIDOS,
            pedido__data_pedido__date__gte=inicio,
            pedido__data_pedido__date__lte=fim,
        )
        .values("material__tipo")
        .annotate(total=Sum("valor_total"))
    )
    return {
        row["material__tipo"]: (row["total"] or Decimal("0.00"))
        for row in qs
    }

# ═════════════════════════════════════════════════════════════
# 2. QUALITATIVO (Verba × Gasto)
# ═════════════════════════════════════════════════════════════

def relatorio_qualitativo(contrato_ids, ano, mes_ini, mes_fim, ano_fim=None):
    contrato_ids = _normalizar_contratos(contrato_ids)
    ano_ini, mes_ini, ano_fim, mes_fim = _normalizar_periodo(
        ano, mes_ini, ano_fim, mes_fim
    )
    if not contrato_ids:
        return _qualitativo_vazio()

    meses = _meses_periodo(ano_ini, mes_ini, ano_fim, mes_fim)
    mg = _mapa_gasto(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim)
    mv = _mapa_verba(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim)

    # ── Resumo por categoria (período inteiro) ──
    resumo_categorias = []
    total_verba_geral = ZERO
    total_gasto_geral = ZERO
    for cod, label in CATEGORIAS:
        verba = sum(
            (_v(mv, cid, a, m, cod) for cid in contrato_ids for a, m in meses),
            ZERO,
        )
        gasto = sum(
            (_g(mg, cid, a, m, cod) for cid in contrato_ids for a, m in meses),
            ZERO,
        )
        saldo = verba - gasto
        pct = _pct(gasto, verba)
        resumo_categorias.append({
            "categoria": cod, "categoria_label": label,
            "verba": _q(verba), "gasto": _q(gasto), "saldo": _q(saldo),
            "pct_uso": pct,
            "status": "acima" if saldo < 0 else ("alerta" if pct >= 80 else "ok"),
        })
        total_verba_geral += verba
        total_gasto_geral += gasto

    # ── Evolução mensal ──
    evolucao_mensal = []
    for a, m in meses:
        d = {"label": _label_mes(a, m), "ano": a, "mes": m}
        vt = gt = ZERO
        for cod, _label in CATEGORIAS:
            verba = sum((_v(mv, cid, a, m, cod) for cid in contrato_ids), ZERO)
            gasto = sum((_g(mg, cid, a, m, cod) for cid in contrato_ids), ZERO)
            d[f"verba_{cod.lower()}"] = _q(verba)
            d[f"gasto_{cod.lower()}"] = _q(gasto)
            d[f"saldo_{cod.lower()}"] = _q(verba - gasto)
            vt += verba
            gt += gasto
        d["verba_total"] = _q(vt)
        d["gasto_total"] = _q(gt)
        d["saldo_total"] = _q(vt - gt)
        evolucao_mensal.append(d)

    # ── Por contrato ──
    contratos = {c.id: c for c in Contrato.objects.filter(id__in=contrato_ids)}
    por_contrato = []
    for cid in contrato_ids:
        ct = contratos.get(cid)
        if not ct:
            continue
        d = {"contrato": f"{ct.cm} — {ct.cliente}",
             "contrato_id": cid, "categorias": []}
        vct = gct = ZERO
        for cod, label in CATEGORIAS:
            verba = sum((_v(mv, cid, a, m, cod) for a, m in meses), ZERO)
            gasto = sum((_g(mg, cid, a, m, cod) for a, m in meses), ZERO)
            d["categorias"].append({
                "categoria": cod, "categoria_label": label,
                "verba": _q(verba), "gasto": _q(gasto),
                "saldo": _q(verba - gasto), "pct_uso": _pct(gasto, verba),
            })
            vct += verba
            gct += gasto
        d["verba_total"] = _q(vct)
        d["gasto_total"] = _q(gct)
        d["saldo_total"] = _q(vct - gct)
        por_contrato.append(d)

    return {
        "resumo_categorias": resumo_categorias,
        "total_verba_geral": _q(total_verba_geral),
        "total_gasto_geral": _q(total_gasto_geral),
        "saldo_geral": _q(total_verba_geral - total_gasto_geral),
        "pct_uso_geral": _pct(total_gasto_geral, total_verba_geral),
        "evolucao_mensal": evolucao_mensal,
        "por_contrato": por_contrato,
    }


def _qualitativo_vazio():
    return {
        "resumo_categorias": [
            {"categoria": c, "categoria_label": l, "verba": ZERO, "gasto": ZERO,
             "saldo": ZERO, "pct_uso": ZERO, "status": "ok"}
            for c, l in CATEGORIAS
        ],
        "total_verba_geral": ZERO, "total_gasto_geral": ZERO,
        "saldo_geral": ZERO, "pct_uso_geral": ZERO,
        "evolucao_mensal": [], "por_contrato": [],
    }


# ═════════════════════════════════════════════════════════════
# 3. ALERTAS (Gastos acima da meta)
# ═════════════════════════════════════════════════════════════

def relatorio_alertas(contrato_ids, ano, mes_ini, mes_fim, ano_fim=None):
    contrato_ids = _normalizar_contratos(contrato_ids)
    ano_ini, mes_ini, ano_fim, mes_fim = _normalizar_periodo(
        ano, mes_ini, ano_fim, mes_fim
    )
    if not contrato_ids:
        return {"alertas": [], "total_alertas": 0, "total_excesso_geral": ZERO,
                "resumo_excesso": [], "contratos_criticos": []}

    meses = _meses_periodo(ano_ini, mes_ini, ano_fim, mes_fim)
    mg = _mapa_gasto(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim)
    mv = _mapa_verba(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim)
    contratos = {c.id: c for c in Contrato.objects.filter(id__in=contrato_ids)}

    alertas = []
    excesso_por_cat = defaultdict(lambda: ZERO)
    desvios_por_contrato = defaultdict(int)

    # Itera SÓ sobre as chaves de verba existentes (não produto cartesiano)
    for (cid, a, m, cod) in mv.keys():
        if (a, m) not in meses or cid not in contratos:
            continue
        verba = _v(mv, cid, a, m, cod)
        if verba <= 0:
            continue
        gasto = _g(mg, cid, a, m, cod)
        if gasto > verba:
            excesso = gasto - verba
            pct = _pct(excesso, verba)
            ct = contratos[cid]
            alertas.append({
                "contrato": f"{ct.cm} — {ct.cliente}", "contrato_id": cid,
                "mes_label": _label_mes(a, m), "ano": a, "mes": m,
                "categoria": cod,
                "categoria_label": dict(CATEGORIAS)[cod],
                "verba": _q(verba), "gasto": _q(gasto), "excesso": _q(excesso),
                "pct_excesso": pct,
                "severidade": ("critico" if pct > 30
                               else "alto" if pct > 15 else "moderado"),
            })
            excesso_por_cat[cod] += excesso
            desvios_por_contrato[ct.cm] += 1

    alertas.sort(key=lambda x: x["excesso"], reverse=True)

    resumo_excesso = [
        {"categoria": c, "categoria_label": l,
         "total_excesso": _q(excesso_por_cat.get(c, ZERO))}
        for c, l in CATEGORIAS
    ]
    contratos_criticos = sorted(
        ({"contrato": k, "desvios": v} for k, v in desvios_por_contrato.items()),
        key=lambda x: x["desvios"], reverse=True,
    )[:10]

    return {
        "alertas": alertas,
        "total_alertas": len(alertas),
        "total_excesso_geral": _q(sum(excesso_por_cat.values(), ZERO)),
        "resumo_excesso": resumo_excesso,
        "contratos_criticos": contratos_criticos,
    }


# ═════════════════════════════════════════════════════════════
# 4. ECONOMIAS
# ═════════════════════════════════════════════════════════════

def relatorio_economias(contrato_ids, ano, mes_ini, mes_fim, ano_fim=None):
    contrato_ids = _normalizar_contratos(contrato_ids)
    ano_ini, mes_ini, ano_fim, mes_fim = _normalizar_periodo(
        ano, mes_ini, ano_fim, mes_fim
    )
    if not contrato_ids:
        return {"economias": [], "total_economias": 0,
                "total_economia_geral": ZERO, "resumo_economia": [],
                "ranking_contratos": []}

    meses = _meses_periodo(ano_ini, mes_ini, ano_fim, mes_fim)
    mg = _mapa_gasto(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim)
    mv = _mapa_verba(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim)
    contratos = {c.id: c for c in Contrato.objects.filter(id__in=contrato_ids)}

    economias = []
    economia_por_cat = defaultdict(lambda: ZERO)
    economia_por_contrato = defaultdict(lambda: ZERO)

    for (cid, a, m, cod) in mv.keys():
        if (a, m) not in meses or cid not in contratos:
            continue
        verba = _v(mv, cid, a, m, cod)
        if verba <= 0:
            continue
        gasto = _g(mg, cid, a, m, cod)
        if gasto < verba:
            economia = verba - gasto
            ct = contratos[cid]
            economias.append({
                "contrato": f"{ct.cm} — {ct.cliente}", "contrato_id": cid,
                "mes_label": _label_mes(a, m), "ano": a, "mes": m,
                "categoria": cod, "categoria_label": dict(CATEGORIAS)[cod],
                "verba": _q(verba), "gasto": _q(gasto),
                "economia": _q(economia), "pct_economia": _pct(economia, verba),
            })
            economia_por_cat[cod] += economia
            economia_por_contrato[ct.cm] += economia

    economias.sort(key=lambda x: x["economia"], reverse=True)

    resumo_economia = [
        {"categoria": c, "categoria_label": l,
         "total_economia": _q(economia_por_cat.get(c, ZERO))}
        for c, l in CATEGORIAS
    ]
    ranking_contratos = sorted(
        ({"contrato": k, "economia": _q(v)}
         for k, v in economia_por_contrato.items()),
        key=lambda x: x["economia"], reverse=True,
    )[:10]

    return {
        "economias": economias,
        "total_economias": len(economias),
        "total_economia_geral": _q(sum(economia_por_cat.values(), ZERO)),
        "resumo_economia": resumo_economia,
        "ranking_contratos": ranking_contratos,
    }


# ═════════════════════════════════════════════════════════════
# 5. ESTIMATIVAS / PROJEÇÕES
# ═════════════════════════════════════════════════════════════

def relatorio_estimativas(contrato_ids, ano, mes_atual, n_historico=6, n_proj=6):
    contrato_ids = _normalizar_contratos(contrato_ids)
    if not (1 <= int(mes_atual) <= 12):
        raise ValueError(f"mes_atual inválido: {mes_atual}")
    if not contrato_ids:
        return {"media_por_categoria": {}, "historico_mensal": [],
                "projecao": [], "meses_historico_labels": []}

    # Histórico: n meses ANTERIORES a (ano, mes_atual)
    meses_hist = []
    a, m = ano, mes_atual
    for _ in range(n_historico):
        m -= 1
        if m <= 0:
            m, a = 12, a - 1
        meses_hist.append((a, m))
    meses_hist.reverse()

    ano_ini, mes_ini = meses_hist[0]
    ano_fim, mes_fim = meses_hist[-1]
    mg = _mapa_gasto(contrato_ids, ano_ini, mes_ini, ano_fim, mes_fim)

    # gasto total por (ano, mes, cod) somando contratos
    def gasto_mes(a, m, cod):
        return sum((_g(mg, cid, a, m, cod) for cid in contrato_ids), ZERO)

    media_por_cat = {}
    for cod, label in CATEGORIAS:
        hist = [gasto_mes(ah, mh, cod) for ah, mh in meses_hist]
        n = len(hist) or 1
        media = (sum(hist, ZERO) / n)
        info = {
            "media": _q(media), "label": label,
            "historico": [_q(x) for x in hist],
            "min": _q(min(hist)) if hist else ZERO,
            "max": _q(max(hist)) if hist else ZERO,
        }
        if len(hist) >= 6:
            recente = sum(hist[3:], ZERO) / 3
            antiga = sum(hist[:3], ZERO) / 3
            info["tendencia"] = (
                "subindo" if recente > antiga * Decimal("1.05")
                else "descendo" if recente < antiga * Decimal("0.95")
                else "estavel"
            )
            info["variacao_tendencia"] = _variacao_pct(recente, antiga)
        else:
            info["tendencia"] = "insuficiente"
            info["variacao_tendencia"] = ZERO
        media_por_cat[cod] = info

    # Histórico mensal (gráfico)
    historico_mensal = []
    for i, (ah, mh) in enumerate(meses_hist):
        d = {"label": _label_mes(ah, mh), "ano": ah, "mes": mh,
             "tipo": "historico"}
        tot = ZERO
        for cod, _l in CATEGORIAS:
            val = media_por_cat[cod]["historico"][i]
            d[f"gasto_{cod.lower()}"] = val
            tot += val
        d["gasto_total"] = _q(tot)
        historico_mensal.append(d)

    # Projeção: próximos n meses, comparando com verba planejada
    a_proj, m_proj = ano, mes_atual
    meses_proj = []
    for _ in range(n_proj):
        m_proj += 1
        if m_proj > 12:
            m_proj, a_proj = 1, a_proj + 1
        meses_proj.append((a_proj, m_proj))

    pa, pm = meses_proj[0]
    pa_f, pm_f = meses_proj[-1]
    mv_proj = _mapa_verba(contrato_ids, pa, pm, pa_f, pm_f)

    projecao = []
    for (ap, mp) in meses_proj:
        d = {"label": _label_mes(ap, mp), "ano": ap, "mes": mp,
             "tipo": "projecao"}
        vt = gt = ZERO
        for cod, _l in CATEGORIAS:
            verba = sum((mv_proj.get((cid, ap, mp, cod), ZERO)
                         for cid in contrato_ids), ZERO)
            gasto = media_por_cat[cod]["media"]
            d[f"verba_{cod.lower()}"] = _q(verba)
            d[f"gasto_{cod.lower()}"] = _q(gasto)
            d[f"saldo_{cod.lower()}"] = _q(verba - gasto)
            vt += verba
            gt += gasto
        d["verba_total"] = _q(vt)
        d["gasto_total"] = _q(gt)
        d["saldo_total"] = _q(vt - gt)
        projecao.append(d)

    return {
        "media_por_categoria": media_por_cat,
        "historico_mensal": historico_mensal,
        "projecao": projecao,
        "meses_historico_labels": [_label_mes(a, m) for a, m in meses_hist],
    }


# ═════════════════════════════════════════════════════════════
# 6. CONSOLIDADO
# ═════════════════════════════════════════════════════════════

def gerar_relatorio_completo(contrato_ids, ano, mes_ini, mes_fim, ano_fim=None):
    contrato_ids = _normalizar_contratos(contrato_ids)
    ano_ini, mes_ini, ano_fim, mes_fim = _normalizar_periodo(
        ano, mes_ini, ano_fim, mes_fim
    )
    hoje = date.today()

    return {
        "parametros": {
            "ano": ano_ini, "ano_fim": ano_fim,
            "mes_ini": mes_ini, "mes_fim": mes_fim,
            "periodo_label": (
                f"{_label_mes(ano_ini, mes_ini)} a "
                f"{_label_mes(ano_fim, mes_fim)}"
            ),
            "gerado_em": hoje,
        },
        "quantitativo": relatorio_quantitativo(
            contrato_ids, ano_ini, mes_ini, mes_fim, ano_fim),
        "qualitativo": relatorio_qualitativo(
            contrato_ids, ano_ini, mes_ini, mes_fim, ano_fim),
        "alertas": relatorio_alertas(
            contrato_ids, ano_ini, mes_ini, mes_fim, ano_fim),
        "economias": relatorio_economias(
            contrato_ids, ano_ini, mes_ini, mes_fim, ano_fim),
        "estimativas": relatorio_estimativas(
            contrato_ids, ano_ini, hoje.month),
    }

