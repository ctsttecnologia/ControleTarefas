
# suprimentos/relatorios.py

"""
Módulo de relatórios gerenciais do Suprimentos.
Centraliza toda a lógica de consulta e cálculo para:
  - Quantitativo (quantidades por categoria, contrato, período)
  - Qualitativo (verba × gasto real × meta)
  - Gastos acima da meta (alertas e desvios)
  - Economias (onde sobrou verba)
  - Estimativas (projeção de gasto próximos meses)
"""

import logging
from collections import defaultdict
from decimal import Decimal
from datetime import date

from django.db.models import Sum, Count, F, Q, Avg, DecimalField
from django.db.models.functions import Coalesce, TruncMonth

from .models import (
    Contrato, VerbaContrato, Pedido, ItemPedido,
    Material, CategoriaMaterial, EstoqueConsumo,
)

logger = logging.getLogger(__name__)

ZERO = Decimal('0.00')
STATUS_COMPRA = ['APROVADO', 'ENTREGUE', 'RECEBIDO']
CATEGORIAS = [
    ('EPI', 'EPI'),
    ('CONSUMO', 'Consumo'),
    ('FERRAMENTA', 'Ferramenta'),
]


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════

def _meses_periodo(ano_ini, mes_ini, ano_fim, mes_fim):
    """Gera lista de tuplas (ano, mes) entre dois períodos inclusive."""
    meses = []
    a, m = ano_ini, mes_ini
    while (a, m) <= (ano_fim, mes_fim):
        meses.append((a, m))
        m += 1
        if m > 12:
            m = 1
            a += 1
    return meses


def _label_mes(ano, mes):
    """Retorna label amigável: 'Jan/2026'."""
    nomes = [
        '', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
    ]
    return f"{nomes[mes]}/{ano}"


def _pct(parte, total):
    """Calcula percentual seguro (evita divisão por zero)."""
    if not total or total == 0:
        return Decimal('0.00')
    return round((parte / total) * 100, 2)


def _variacao_pct(atual, anterior):
    """Calcula variação percentual entre dois valores."""
    if not anterior or anterior == 0:
        if atual and atual > 0:
            return Decimal('100.00')
        return Decimal('0.00')
    return round(((atual - anterior) / anterior) * 100, 2)


# ═══════════════════════════════════════════════════════
# 1. QUANTITATIVO
# ═══════════════════════════════════════════════════════

def relatorio_quantitativo(contrato_ids, ano, mes_ini, mes_fim):
    """
    Retorna dados quantitativos de compras por categoria e período.

    Returns:
        dict com:
        - resumo_geral: totais por categoria
        - por_mes: lista mês a mês com quantidades e valores
        - top_materiais: materiais mais comprados
        - por_contrato: breakdown por contrato
    """
    meses = _meses_periodo(ano, mes_ini, ano, mes_fim)

    # ── Base query: Itens de pedidos com status de compra ──
    itens_base = ItemPedido.objects.filter(
        pedido__contrato_id__in=contrato_ids,
        pedido__status__in=STATUS_COMPRA,
        pedido__data_pedido__year=ano,
        pedido__data_pedido__month__gte=mes_ini,
        pedido__data_pedido__month__lte=mes_fim,
    ).select_related('material', 'pedido__contrato')

    # ── Resumo geral por categoria ──
    resumo_geral = []
    for cod, label in CATEGORIAS:
        qs = itens_base.filter(material__classificacao=cod)
        agg = qs.aggregate(
            total_qtd=Coalesce(Sum('quantidade'), 0),
            total_valor=Coalesce(Sum('valor_total'), ZERO, output_field=DecimalField()),
            total_itens=Count('id'),
            total_pedidos=Count('pedido', distinct=True),
        )
        resumo_geral.append({
            'categoria': cod,
            'categoria_label': label,
            'qtd_itens_linha': agg['total_itens'],
            'qtd_pedidos': agg['total_pedidos'],
            'qtd_unidades': agg['total_qtd'],
            'valor_total': agg['total_valor'],
        })

    total_geral_valor = sum(r['valor_total'] for r in resumo_geral)
    for r in resumo_geral:
        r['pct_valor'] = _pct(r['valor_total'], total_geral_valor)

    # ── Por mês ──
    por_mes = []
    for a, m in meses:
        itens_mes = itens_base.filter(
            pedido__data_pedido__year=a,
            pedido__data_pedido__month=m,
        )
        dados_mes = {'label': _label_mes(a, m), 'ano': a, 'mes': m}
        total_mes = ZERO
        for cod, label in CATEGORIAS:
            agg = itens_mes.filter(material__classificacao=cod).aggregate(
                qtd=Coalesce(Sum('quantidade'), 0),
                valor=Coalesce(Sum('valor_total'), ZERO, output_field=DecimalField()),
            )
            dados_mes[f'qtd_{cod.lower()}'] = agg['qtd']
            dados_mes[f'valor_{cod.lower()}'] = agg['valor']
            total_mes += agg['valor']
        dados_mes['valor_total'] = total_mes
        por_mes.append(dados_mes)

    # ── Top 15 materiais mais comprados ──
    top_materiais = (
        itens_base
        .values('material__descricao', 'material__classificacao', 'material__unidade')
        .annotate(
            qtd_total=Sum('quantidade'),
            valor_total=Sum('valor_total'),
            vezes_pedido=Count('pedido', distinct=True),
        )
        .order_by('-valor_total')[:15]
    )

    # ── Breakdown por contrato ──
    por_contrato = []
    contratos = Contrato.objects.filter(id__in=contrato_ids, ativo=True)
    for contrato in contratos:
        itens_ct = itens_base.filter(pedido__contrato=contrato)
        dados_ct = {
            'contrato': f"{contrato.cm} — {contrato.cliente}",
            'contrato_id': contrato.id,
        }
        total_ct = ZERO
        for cod, label in CATEGORIAS:
            agg = itens_ct.filter(material__classificacao=cod).aggregate(
                valor=Coalesce(Sum('valor_total'), ZERO, output_field=DecimalField()),
                qtd=Coalesce(Sum('quantidade'), 0),
            )
            dados_ct[f'valor_{cod.lower()}'] = agg['valor']
            dados_ct[f'qtd_{cod.lower()}'] = agg['qtd']
            total_ct += agg['valor']
        dados_ct['valor_total'] = total_ct
        if total_ct > 0:
            por_contrato.append(dados_ct)

    por_contrato.sort(key=lambda x: x['valor_total'], reverse=True)

    return {
        'resumo_geral': resumo_geral,
        'total_geral_valor': total_geral_valor,
        'por_mes': por_mes,
        'top_materiais': list(top_materiais),
        'por_contrato': por_contrato,
    }


# ═══════════════════════════════════════════════════════
# 2. QUALITATIVO (Verba × Gasto × Meta)
# ═══════════════════════════════════════════════════════

def relatorio_qualitativo(contrato_ids, ano, mes_ini, mes_fim):
    """
    Comparação verba × gasto real por categoria, contrato e mês.

    Returns:
        dict com:
        - resumo_categorias: por categoria (verba, gasto, saldo, %)
        - por_contrato_mes: tabela detalhada contrato × mês
        - evolucao_mensal: série temporal verba vs gasto
    """
    meses = _meses_periodo(ano, mes_ini, ano, mes_fim)

    # ── Resumo por categoria (período inteiro) ──
    resumo_categorias = []
    total_verba_geral = ZERO
    total_gasto_geral = ZERO

    for cod, label in CATEGORIAS:
        campo_verba = f'verba_{cod.lower()}'

        # Verba total
        verba = VerbaContrato.objects.filter(
            contrato_id__in=contrato_ids,
            ano=ano, mes__gte=mes_ini, mes__lte=mes_fim,
        ).aggregate(
            total=Coalesce(Sum(campo_verba), ZERO, output_field=DecimalField())
        )['total']

        # Gasto total
        gasto = ItemPedido.objects.filter(
            pedido__contrato_id__in=contrato_ids,
            pedido__status__in=STATUS_COMPRA,
            pedido__data_pedido__year=ano,
            pedido__data_pedido__month__gte=mes_ini,
            pedido__data_pedido__month__lte=mes_fim,
            material__classificacao=cod,
        ).aggregate(
            total=Coalesce(Sum('valor_total'), ZERO, output_field=DecimalField())
        )['total']

        saldo = verba - gasto
        pct_uso = _pct(gasto, verba)

        resumo_categorias.append({
            'categoria': cod,
            'categoria_label': label,
            'verba': verba,
            'gasto': gasto,
            'saldo': saldo,
            'pct_uso': pct_uso,
            'status': 'acima' if saldo < 0 else ('alerta' if pct_uso >= 80 else 'ok'),
        })
        total_verba_geral += verba
        total_gasto_geral += gasto

    # ── Evolução mensal (verba vs gasto) ──
    evolucao_mensal = []
    for a, m in meses:
        dado = {'label': _label_mes(a, m), 'ano': a, 'mes': m}
        for cod, label in CATEGORIAS:
            campo_verba = f'verba_{cod.lower()}'
            verba_mes = VerbaContrato.objects.filter(
                contrato_id__in=contrato_ids, ano=a, mes=m,
            ).aggregate(
                total=Coalesce(Sum(campo_verba), ZERO, output_field=DecimalField())
            )['total']

            gasto_mes = ItemPedido.objects.filter(
                pedido__contrato_id__in=contrato_ids,
                pedido__status__in=STATUS_COMPRA,
                pedido__data_pedido__year=a,
                pedido__data_pedido__month=m,
                material__classificacao=cod,
            ).aggregate(
                total=Coalesce(Sum('valor_total'), ZERO, output_field=DecimalField())
            )['total']

            dado[f'verba_{cod.lower()}'] = verba_mes
            dado[f'gasto_{cod.lower()}'] = gasto_mes
            dado[f'saldo_{cod.lower()}'] = verba_mes - gasto_mes

        dado['verba_total'] = sum(
            dado[f'verba_{c.lower()}'] for c, _ in CATEGORIAS
        )
        dado['gasto_total'] = sum(
            dado[f'gasto_{c.lower()}'] for c, _ in CATEGORIAS
        )
        dado['saldo_total'] = dado['verba_total'] - dado['gasto_total']
        evolucao_mensal.append(dado)

    # ── Por contrato (período inteiro) ──
    por_contrato = []
    contratos = Contrato.objects.filter(id__in=contrato_ids, ativo=True)
    for contrato in contratos:
        dados_ct = {
            'contrato': f"{contrato.cm} — {contrato.cliente}",
            'contrato_id': contrato.id,
            'categorias': [],
        }
        total_verba_ct = ZERO
        total_gasto_ct = ZERO

        for cod, label in CATEGORIAS:
            campo_verba = f'verba_{cod.lower()}'
            verba_ct = VerbaContrato.objects.filter(
                contrato=contrato, ano=ano,
                mes__gte=mes_ini, mes__lte=mes_fim,
            ).aggregate(
                total=Coalesce(Sum(campo_verba), ZERO, output_field=DecimalField())
            )['total']

            gasto_ct = ItemPedido.objects.filter(
                pedido__contrato=contrato,
                pedido__status__in=STATUS_COMPRA,
                pedido__data_pedido__year=ano,
                pedido__data_pedido__month__gte=mes_ini,
                pedido__data_pedido__month__lte=mes_fim,
                material__classificacao=cod,
            ).aggregate(
                total=Coalesce(Sum('valor_total'), ZERO, output_field=DecimalField())
            )['total']

            saldo_ct = verba_ct - gasto_ct
            dados_ct['categorias'].append({
                'categoria': cod,
                'categoria_label': label,
                'verba': verba_ct,
                'gasto': gasto_ct,
                'saldo': saldo_ct,
                'pct_uso': _pct(gasto_ct, verba_ct),
            })
            total_verba_ct += verba_ct
            total_gasto_ct += gasto_ct

        dados_ct['verba_total'] = total_verba_ct
        dados_ct['gasto_total'] = total_gasto_ct
        dados_ct['saldo_total'] = total_verba_ct - total_gasto_ct
        por_contrato.append(dados_ct)

    return {
        'resumo_categorias': resumo_categorias,
        'total_verba_geral': total_verba_geral,
        'total_gasto_geral': total_gasto_geral,
        'saldo_geral': total_verba_geral - total_gasto_geral,
        'pct_uso_geral': _pct(total_gasto_geral, total_verba_geral),
        'evolucao_mensal': evolucao_mensal,
        'por_contrato': por_contrato,
    }


# ═══════════════════════════════════════════════════════
# 3. GASTOS ACIMA DA META (Alertas)
# ═══════════════════════════════════════════════════════

def relatorio_alertas(contrato_ids, ano, mes_ini, mes_fim):
    """
    Identifica todos os desvios: meses/categorias/contratos
    onde o gasto ultrapassou a verba.

    Returns:
        dict com:
        - alertas: lista de desvios (contrato, mês, cat, verba, gasto, excesso)
        - resumo_excesso: totais de excesso por categoria
        - contratos_criticos: contratos com mais desvios
    """
    meses = _meses_periodo(ano, mes_ini, ano, mes_fim)
    alertas = []
    excesso_por_cat = defaultdict(lambda: ZERO)
    desvios_por_contrato = defaultdict(int)

    contratos = Contrato.objects.filter(id__in=contrato_ids, ativo=True)

    for contrato in contratos:
        for a, m in meses:
            for cod, label in CATEGORIAS:
                campo_verba = f'verba_{cod.lower()}'

                verba = VerbaContrato.objects.filter(
                    contrato=contrato, ano=a, mes=m,
                ).aggregate(
                    total=Coalesce(Sum(campo_verba), ZERO, output_field=DecimalField())
                )['total']

                gasto = ItemPedido.objects.filter(
                    pedido__contrato=contrato,
                    pedido__status__in=STATUS_COMPRA,
                    pedido__data_pedido__year=a,
                    pedido__data_pedido__month=m,
                    material__classificacao=cod,
                ).aggregate(
                    total=Coalesce(Sum('valor_total'), ZERO, output_field=DecimalField())
                )['total']

                if gasto > verba and verba > 0:
                    excesso = gasto - verba
                    pct_excesso = _pct(excesso, verba)
                    alertas.append({
                        'contrato': f"{contrato.cm} — {contrato.cliente}",
                        'contrato_id': contrato.id,
                        'mes_label': _label_mes(a, m),
                        'ano': a,
                        'mes': m,
                        'categoria': cod,
                        'categoria_label': label,
                        'verba': verba,
                        'gasto': gasto,
                        'excesso': excesso,
                        'pct_excesso': pct_excesso,
                        'severidade': (
                            'critico' if pct_excesso > 30
                            else 'alto' if pct_excesso > 15
                            else 'moderado'
                        ),
                    })
                    excesso_por_cat[cod] += excesso
                    desvios_por_contrato[contrato.cm] += 1

    # Ordenar por excesso (maior primeiro)
    alertas.sort(key=lambda x: x['excesso'], reverse=True)

    # Resumo excesso por categoria
    resumo_excesso = [
        {
            'categoria': cod,
            'categoria_label': label,
            'total_excesso': excesso_por_cat.get(cod, ZERO),
        }
        for cod, label in CATEGORIAS
    ]

    # Contratos com mais desvios
    contratos_criticos = sorted(
        [{'contrato': k, 'desvios': v} for k, v in desvios_por_contrato.items()],
        key=lambda x: x['desvios'], reverse=True
    )[:10]

    return {
        'alertas': alertas,
        'total_alertas': len(alertas),
        'total_excesso_geral': sum(excesso_por_cat.values(), ZERO),
        'resumo_excesso': resumo_excesso,
        'contratos_criticos': contratos_criticos,
    }


# ═══════════════════════════════════════════════════════
# 4. ECONOMIAS
# ═══════════════════════════════════════════════════════

def relatorio_economias(contrato_ids, ano, mes_ini, mes_fim):
    """
    Identifica onde sobrou verba (economia real).

    Returns:
        dict com:
        - economias: lista por contrato/mês/cat com verba sobrando
        - resumo_economia: totais economizados por categoria
        - ranking_contratos: contratos que mais economizaram
    """
    meses = _meses_periodo(ano, mes_ini, ano, mes_fim)
    economias = []
    economia_por_cat = defaultdict(lambda: ZERO)
    economia_por_contrato = defaultdict(lambda: ZERO)

    contratos = Contrato.objects.filter(id__in=contrato_ids, ativo=True)

    for contrato in contratos:
        for a, m in meses:
            for cod, label in CATEGORIAS:
                campo_verba = f'verba_{cod.lower()}'

                verba = VerbaContrato.objects.filter(
                    contrato=contrato, ano=a, mes=m,
                ).aggregate(
                    total=Coalesce(Sum(campo_verba), ZERO, output_field=DecimalField())
                )['total']

                gasto = ItemPedido.objects.filter(
                    pedido__contrato=contrato,
                    pedido__status__in=STATUS_COMPRA,
                    pedido__data_pedido__year=a,
                    pedido__data_pedido__month=m,
                    material__classificacao=cod,
                ).aggregate(
                    total=Coalesce(Sum('valor_total'), ZERO, output_field=DecimalField())
                )['total']

                if verba > 0 and gasto < verba:
                    economia = verba - gasto
                    pct_economia = _pct(economia, verba)
                    economias.append({
                        'contrato': f"{contrato.cm} — {contrato.cliente}",
                        'contrato_id': contrato.id,
                        'mes_label': _label_mes(a, m),
                        'ano': a,
                        'mes': m,
                        'categoria': cod,
                        'categoria_label': label,
                        'verba': verba,
                        'gasto': gasto,
                        'economia': economia,
                        'pct_economia': pct_economia,
                    })
                    economia_por_cat[cod] += economia
                    economia_por_contrato[contrato.cm] += economia

    economias.sort(key=lambda x: x['economia'], reverse=True)

    resumo_economia = [
        {
            'categoria': cod,
            'categoria_label': label,
            'total_economia': economia_por_cat.get(cod, ZERO),
        }
        for cod, label in CATEGORIAS
    ]

    ranking_contratos = sorted(
        [{'contrato': k, 'economia': v} for k, v in economia_por_contrato.items()],
        key=lambda x: x['economia'], reverse=True
    )[:10]

    return {
        'economias': economias,
        'total_economias': len(economias),
        'total_economia_geral': sum(economia_por_cat.values(), ZERO),
        'resumo_economia': resumo_economia,
        'ranking_contratos': ranking_contratos,
    }


# ═══════════════════════════════════════════════════════
# 5. ESTIMATIVAS / PROJEÇÕES
# ═══════════════════════════════════════════════════════

def relatorio_estimativas(contrato_ids, ano, mes_atual):
    """
    Projeta gastos para os próximos meses baseado na média histórica.

    Usa média móvel dos últimos 6 meses e compara com verba planejada.

    Returns:
        dict com:
        - media_mensal: gasto médio por categoria (últimos 6 meses)
        - projecao: próximos 6 meses com gasto estimado vs verba
        - tendencia: se está subindo ou descendo
    """
    # Últimos 6 meses de gasto real
    meses_historico = []
    a, m = ano, mes_atual
    for _ in range(6):
        m -= 1
        if m <= 0:
            m = 12
            a -= 1
        meses_historico.append((a, m))
    meses_historico.reverse()

    # Calcular média por categoria
    media_por_cat = {}
    historico_mensal = []

    for cod, label in CATEGORIAS:
        gastos_hist = []
        for ah, mh in meses_historico:
            gasto = ItemPedido.objects.filter(
                pedido__contrato_id__in=contrato_ids,
                pedido__status__in=STATUS_COMPRA,
                pedido__data_pedido__year=ah,
                pedido__data_pedido__month=mh,
                material__classificacao=cod,
            ).aggregate(
                total=Coalesce(Sum('valor_total'), ZERO, output_field=DecimalField())
            )['total']
            gastos_hist.append(gasto)

        media = sum(gastos_hist) / len(gastos_hist) if gastos_hist else ZERO
        media_por_cat[cod] = {
            'media': round(media, 2),
            'label': label,
            'historico': gastos_hist,
            'min': min(gastos_hist) if gastos_hist else ZERO,
            'max': max(gastos_hist) if gastos_hist else ZERO,
        }

        # Tendência: comparar média dos 3 últimos vs 3 primeiros
        if len(gastos_hist) >= 6:
            media_recente = sum(gastos_hist[3:]) / 3
            media_antiga = sum(gastos_hist[:3]) / 3
            media_por_cat[cod]['tendencia'] = (
                'subindo' if media_recente > media_antiga * Decimal('1.05')
                else 'descendo' if media_recente < media_antiga * Decimal('0.95')
                else 'estavel'
            )
            media_por_cat[cod]['variacao_tendencia'] = _variacao_pct(media_recente, media_antiga)
        else:
            media_por_cat[cod]['tendencia'] = 'insuficiente'
            media_por_cat[cod]['variacao_tendencia'] = ZERO

    # Histórico mensal completo (para gráfico)
    for i, (ah, mh) in enumerate(meses_historico):
        dado = {'label': _label_mes(ah, mh), 'ano': ah, 'mes': mh, 'tipo': 'historico'}
        for cod, label in CATEGORIAS:
            dado[f'gasto_{cod.lower()}'] = media_por_cat[cod]['historico'][i]
        dado['gasto_total'] = sum(
            dado[f'gasto_{c.lower()}'] for c, _ in CATEGORIAS
        )
        historico_mensal.append(dado)

    # Projeção próximos 6 meses
    projecao = []
    a_proj, m_proj = ano, mes_atual
    for _ in range(6):
        m_proj += 1
        if m_proj > 12:
            m_proj = 1
            a_proj += 1

        dado_proj = {
            'label': _label_mes(a_proj, m_proj),
            'ano': a_proj,
            'mes': m_proj,
            'tipo': 'projecao',
        }

        total_verba_proj = ZERO
        total_gasto_proj = ZERO
        for cod, label in CATEGORIAS:
            campo_verba = f'verba_{cod.lower()}'

            # Verba planejada (se existir)
            verba_plan = VerbaContrato.objects.filter(
                contrato_id__in=contrato_ids,
                ano=a_proj, mes=m_proj,
            ).aggregate(
                total=Coalesce(Sum(campo_verba), ZERO, output_field=DecimalField())
            )['total']

            gasto_est = media_por_cat[cod]['media']
            saldo_est = verba_plan - gasto_est

            dado_proj[f'verba_{cod.lower()}'] = verba_plan
            dado_proj[f'gasto_{cod.lower()}'] = gasto_est
            dado_proj[f'saldo_{cod.lower()}'] = saldo_est
            total_verba_proj += verba_plan
            total_gasto_proj += gasto_est

        dado_proj['verba_total'] = total_verba_proj
        dado_proj['gasto_total'] = total_gasto_proj
        dado_proj['saldo_total'] = total_verba_proj - total_gasto_proj
        projecao.append(dado_proj)

    return {
        'media_por_categoria': media_por_cat,
        'historico_mensal': historico_mensal,
        'projecao': projecao,
        'meses_historico_labels': [_label_mes(a, m) for a, m in meses_historico],
    }


# ═══════════════════════════════════════════════════════
# 6. CONSOLIDADO (chama todos)
# ═══════════════════════════════════════════════════════

def gerar_relatorio_completo(contrato_ids, ano, mes_ini, mes_fim):
    """
    Gera relatório completo consolidado com todas as seções.
    """
    hoje = date.today()

    return {
        'parametros': {
            'ano': ano,
            'mes_ini': mes_ini,
            'mes_fim': mes_fim,
            'periodo_label': f"{_label_mes(ano, mes_ini)} a {_label_mes(ano, mes_fim)}",
            'gerado_em': hoje,
        },
        'quantitativo': relatorio_quantitativo(contrato_ids, ano, mes_ini, mes_fim),
        'qualitativo': relatorio_qualitativo(contrato_ids, ano, mes_ini, mes_fim),
        'alertas': relatorio_alertas(contrato_ids, ano, mes_ini, mes_fim),
        'economias': relatorio_economias(contrato_ids, ano, mes_ini, mes_fim),
        'estimativas': relatorio_estimativas(contrato_ids, ano, hoje.month),
    }

