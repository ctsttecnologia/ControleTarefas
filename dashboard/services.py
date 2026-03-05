
# dashboard/services.py

"""
Camada de serviços do Dashboard.
Centraliza TODAS as queries de métricas para evitar duplicação
entre views.py e admin.py.

Cada função recebe `filial` (ou None para admin global) e retorna
um dicionário pronto para o context do template.
"""

import datetime
import json
from django.db.models import Count, Q, Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone


# =====================================================================
# IMPORTS DOS MODELS (lazy para evitar circular imports)
# =====================================================================

def _get_treinamento_models():
    from treinamentos.models import Treinamento, Participante
    return Treinamento, Participante


def _get_tarefa_model():
    from tarefas.models import Tarefas
    return Tarefas


def _get_epi_models():
    from seguranca_trabalho.models import Equipamento, EntregaEPI, MovimentacaoEstoque
    return Equipamento, EntregaEPI, MovimentacaoEstoque


def _get_documento_model():
    from documentos.models import Documento
    return Documento


def _get_pgr_models():
    """Retorna models do PGR ou None se indisponível."""
    try:
        from pgr_gestao.models import (
            PGRDocumento, RiscoIdentificado, PlanoAcaoPGR, GESGrupoExposicao
        )
        return PGRDocumento, RiscoIdentificado, PlanoAcaoPGR, GESGrupoExposicao
    except ImportError:
        return None, None, None, None


# =====================================================================
# HELPERS
# =====================================================================

def _filial_filter(filial):
    """Retorna dict de filtro por filial. Se None, retorna vazio (admin global)."""
    return {'filial': filial} if filial else {}


def _sum_qty(queryset, field='quantidade'):
    """Soma segura de um campo inteiro, retornando 0 se vazio."""
    return queryset.aggregate(
        total=Coalesce(Sum(field), Value(0, output_field=IntegerField()))
    )['total']


# =====================================================================
# MÉTRICAS: TREINAMENTOS
# =====================================================================

def get_metricas_treinamentos(filial=None, dias_alerta=15):
    """
    Retorna métricas de treinamentos.

    Args:
        filial: Filial para filtrar ou None (admin global).
        dias_alerta: Dias para considerar "próximo do vencimento".

    Returns:
        dict com todas as métricas de treinamentos.
    """
    Treinamento, Participante = _get_treinamento_models()
    filtro = _filial_filter(filial)
    hoje = timezone.now().date()
    limite = hoje + datetime.timedelta(days=dias_alerta)

    qs = Treinamento.objects.filter(**filtro)

    # Contadores
    total = qs.count()
    vencidos = qs.filter(data_vencimento__lt=hoje).count()
    vencimento_proximo = qs.filter(
        data_vencimento__gte=hoje,
        data_vencimento__lte=limite
    ).count()

    # Status breakdown
    status_data = list(qs.values('status').annotate(total=Count('id')))

    # Participantes e presença
    filtro_part = {'funcionario__filial_ativa': filial} if filial else {}
    participantes = Participante.objects.filter(**filtro_part)
    total_participantes = participantes.count()
    presentes = participantes.filter(presente=True).count()
    taxa_presenca = round(
        (presentes / total_participantes * 100) if total_participantes > 0 else 0, 1
    )

    # Próximos treinamentos
    proximos = qs.filter(data_inicio__gte=hoje).order_by('data_inicio')[:5]

    return {
        'total_treinamentos': total,
        'vencidos': vencidos,
        'vencimento_proximo': vencimento_proximo,
        'status_data': status_data,
        'total_participantes': total_participantes,
        'taxa_presenca': taxa_presenca,
        'proximos_treinamentos': proximos,
    }


# =====================================================================
# MÉTRICAS: TAREFAS
# =====================================================================

def get_metricas_tarefas(filial=None):
    Tarefas = _get_tarefa_model()
    filtro = _filial_filter(filial)

    qs = Tarefas.objects.filter(**filtro)
    total = qs.count()

    atrasadas = qs.filter(
        prazo__lt=timezone.now(),
        status__in=['pendente', 'andamento', 'pausada']
    ).count()

    status_data = list(qs.values('status').annotate(total=Count('id')))
    prioridade_data = list(qs.values('prioridade').annotate(total=Count('id')))

    # progresso é @property (não é campo do banco)
    # NÃO usar .only() — iterar o queryset normal
    progresso_medio = 0
    if total > 0:
        tarefas_list = list(qs)
        progresso_total = sum(t.progresso for t in tarefas_list)
        progresso_medio = round(progresso_total / total, 1)

    proximas = qs.filter(
        prazo__gte=timezone.now(),
        status__in=['pendente', 'andamento']
    ).order_by('prazo')[:6]

    return {
        'total_tarefas': total,
        'tarefas_atrasadas': atrasadas,
        'status_data': status_data,
        'prioridade_data': prioridade_data,
        'progresso_medio': progresso_medio,
        'tarefas_proximas': proximas,
    }


# =====================================================================
# MÉTRICAS: EPI
# =====================================================================

def get_metricas_epi(filial=None):
    """
    Retorna métricas de EPI.
    Otimizado: usa aggregation em vez de N+1 queries por equipamento.

    Returns:
        dict com todas as métricas de EPI.
    """
    Equipamento, EntregaEPI, MovimentacaoEstoque = _get_epi_models()
    filtro = _filial_filter(filial)
    hoje = timezone.now().date()
    limite_aviso = hoje + datetime.timedelta(days=30)

    # ── Entregas ──
    entregas = EntregaEPI.objects.filter(**filtro).select_related('equipamento')
    total_entregas = entregas.count()

    entregas_sem_assinatura = entregas.filter(
        Q(assinatura_recebimento='') | Q(assinatura_recebimento__isnull=True),
        Q(assinatura_imagem__isnull=True),
    ).count()

    # Vencimento de uso (requer iteração, mas com select_related já otimizado)
    entregas_vencimento_proximo = 0
    for entrega in entregas.only(
        'data_entrega', 'equipamento__vida_util_dias'
    ).select_related('equipamento'):
        if (
            entrega.data_entrega
            and entrega.equipamento
            and entrega.equipamento.vida_util_dias
        ):
            vencimento = entrega.data_entrega + datetime.timedelta(
                days=entrega.equipamento.vida_util_dias
            )
            if hoje <= vencimento <= limite_aviso:
                entregas_vencimento_proximo += 1

    # ── Movimentações (aggregation em batch) ──
    mov_qs = MovimentacaoEstoque.objects.filter(**filtro)

    total_entradas = _sum_qty(mov_qs.filter(tipo='ENTRADA'))
    total_saidas = _sum_qty(mov_qs.filter(tipo='SAIDA'))

    movimentacoes_recentes = mov_qs.select_related(
        'equipamento', 'responsavel'
    ).order_by('-data')[:10]

    # ── Equipamentos e Estoque (batch aggregation ── FIX do N+1) ──
    equipamentos = Equipamento.objects.filter(
        ativo=True, **filtro
    )

    # Uma única query para somar entradas/saídas por equipamento
    estoque_por_equipamento = (
        mov_qs
        .values('equipamento_id', 'tipo')
        .annotate(total=Coalesce(Sum('quantidade'), Value(0, output_field=IntegerField())))
    )

    # Montar lookup: {equip_id: {'ENTRADA': x, 'SAIDA': y}}
    estoque_lookup = {}
    for row in estoque_por_equipamento:
        eq_id = row['equipamento_id']
        if eq_id not in estoque_lookup:
            estoque_lookup[eq_id] = {'ENTRADA': 0, 'SAIDA': 0}
        estoque_lookup[eq_id][row['tipo']] = row['total']

    baixo_estoque = []
    resumo_equipamentos = []

    for eq in equipamentos:
        dados = estoque_lookup.get(eq.pk, {'ENTRADA': 0, 'SAIDA': 0})
        entradas = dados.get('ENTRADA', 0)
        saidas = dados.get('SAIDA', 0)
        estoque_atual = entradas - saidas

        resumo_equipamentos.append({
            'nome': eq.nome,
            'entradas': entradas,
            'saidas': saidas,
            'atual': estoque_atual,
            'min': eq.estoque_minimo,
            'status': (
                'critico' if estoque_atual <= eq.estoque_minimo
                else 'alerta' if estoque_atual <= eq.estoque_minimo + 10
                else 'ok'
            ),
        })

        if estoque_atual <= eq.estoque_minimo:
            baixo_estoque.append({
                'nome': eq.nome,
                'atual': estoque_atual,
                'min': eq.estoque_minimo,
            })

    return {
        'total_entregas': total_entregas,
        'entregas_sem_assinatura': entregas_sem_assinatura,
        'entregas_vencimento_proximo': entregas_vencimento_proximo,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'movimentacoes_recentes': movimentacoes_recentes,
        'equipamentos_estoque_baixo': baixo_estoque,
        'resumo_equipamentos': resumo_equipamentos,
    }


# =====================================================================
# MÉTRICAS: DOCUMENTOS
# =====================================================================

def get_metricas_documentos(filial=None, dias_alerta=30):
    """
    Retorna métricas de documentos.

    Args:
        filial: Filial para filtrar ou None (admin global).
        dias_alerta: Dias para considerar "próximo do vencimento".

    Returns:
        dict com todas as métricas de documentos.
    """
    Documento = _get_documento_model()
    filtro = _filial_filter(filial)
    hoje = timezone.now().date()
    limite = hoje + datetime.timedelta(days=dias_alerta)

    qs = Documento.objects.filter(**filtro)
    total = qs.count()

    status_data = list(qs.values('status').annotate(total=Count('id')))
    vencidos = qs.filter(data_vencimento__lt=hoje).count()
    a_vencer = qs.filter(
        data_vencimento__gte=hoje,
        data_vencimento__lte=limite
    ).count()

    proximos_vencimentos = qs.filter(
        data_vencimento__gte=hoje
    ).order_by('data_vencimento')[:6]

    return {
        'total_documentos': total,
        'status_data': status_data,
        'documentos_vencidos': vencidos,
        'documentos_a_vencer': a_vencer,
        'proximos_vencimentos': proximos_vencimentos,
    }


# =====================================================================
# MÉTRICAS: PGR
# =====================================================================

def pgr_disponivel():
    """Verifica se o módulo PGR está disponível."""
    PGRDocumento, _, _, _ = _get_pgr_models()
    return PGRDocumento is not None


def get_metricas_pgr(filial=None):
    """
    Retorna métricas do PGR.

    Returns:
        dict com todas as métricas do PGR ou None se módulo indisponível.
    """
    PGRDocumento, RiscoIdentificado, PlanoAcaoPGR, GESGrupoExposicao = _get_pgr_models()

    if PGRDocumento is None:
        return None

    filtro = _filial_filter(filial)
    hoje = timezone.now().date()

    # Documentos
    filtro_doc = {'empresa__filial': filial} if filial else {}
    documentos = PGRDocumento.objects.filter(**filtro_doc)

    docs_vigentes = documentos.filter(data_vencimento__gte=hoje).count()
    docs_vencidos = documentos.filter(data_vencimento__lt=hoje).count()
    docs_a_vencer = list(
        documentos.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + datetime.timedelta(days=30)
        ).order_by('data_vencimento')
    )

    # Riscos
    filtro_risco = {'pgr_documento__empresa__filial': filial} if filial else {}
    riscos = RiscoIdentificado.objects.filter(**filtro_risco)

    riscos_criticos = riscos.filter(
        classificacao_risco__in=['critico', 'muito_grave'],
        status_controle__in=['identificado', 'em_controle']
    )

    riscos_classificacao = list(
        riscos.values('classificacao_risco').annotate(total=Count('id')).order_by('classificacao_risco')
    )
    riscos_status = list(
        riscos.values('status_controle').annotate(total=Count('id'))
    )

    # Planos de Ação
    filtro_plano = {'risco_identificado__pgr_documento__empresa__filial': filial} if filial else {}
    planos = PlanoAcaoPGR.objects.filter(**filtro_plano)

    planos_pendentes = planos.filter(status__in=['pendente', 'em_andamento']).count()
    planos_atrasados = planos.filter(
        data_prevista__lt=hoje,
        status__in=['pendente', 'em_andamento']
    ).count()

    # GES
    gess = GESGrupoExposicao.objects.filter(**filtro)

    return {
        'total_documentos': documentos.count(),
        'documentos_vigentes': docs_vigentes,
        'documentos_vencidos': docs_vencidos,
        'documentos_proximo_vencimento': docs_a_vencer,
        'riscos_criticos': riscos_criticos,
        'total_riscos': riscos.count(),
        'planos_pendentes': planos_pendentes,
        'planos_atrasados': planos_atrasados,
        'total_ges': gess.count(),
        'riscos_por_classificacao': json.dumps(riscos_classificacao),
        'riscos_por_status': json.dumps(riscos_status),
        'ultimas_revisoes': documentos.order_by('-atualizado_em')[:5],
        'ultimos_planos': planos.order_by('-criado_em')[:5],
    }


# =====================================================================
# MÉTRICAS: DASHBOARD GERAL (consolidado)
# =====================================================================

def get_metricas_geral(filial=None):
    """
    Retorna métricas consolidadas para o dashboard geral.
    Faz apenas as queries de contagem (leve).

    Returns:
        dict com totais e alertas críticos.
    """
    treinamentos = get_metricas_treinamentos(filial, dias_alerta=15)
    tarefas = get_metricas_tarefas(filial)
    epi = get_metricas_epi(filial)
    documentos = get_metricas_documentos(filial, dias_alerta=30)

    # ── PGR (pode não estar disponível) ──
    total_pgr = 0
    pgr_atrasadas = 0
    if pgr_disponivel():
        metricas_pgr = get_metricas_pgr(filial)
        if metricas_pgr:
            total_pgr = metricas_pgr.get('total_documentos', 0)
            pgr_atrasadas = metricas_pgr.get('planos_atrasados', 0)

    # Alertas críticos
    alertas = []

    if treinamentos['vencimento_proximo'] > 0:
        alertas.append({
            'tipo': 'danger',
            'msg': f"{treinamentos['vencimento_proximo']} treinamento(s) vencendo em 15 dias",
            'icon': 'fas fa-graduation-cap',
        })

    if tarefas['tarefas_atrasadas'] > 0:
        alertas.append({
            'tipo': 'danger',
            'msg': f"{tarefas['tarefas_atrasadas']} tarefa(s) atrasada(s)",
            'icon': 'fas fa-tasks',
        })

    if epi['entregas_sem_assinatura'] > 0:
        alertas.append({
            'tipo': 'warning',
            'msg': f"{epi['entregas_sem_assinatura']} EPI(s) sem assinatura",
            'icon': 'fas fa-signature',
        })

    if documentos['documentos_a_vencer'] > 0:
        alertas.append({
            'tipo': 'warning',
            'msg': f"{documentos['documentos_a_vencer']} documento(s) vencendo em 30 dias",
            'icon': 'fas fa-file-alt',
        })

    if pgr_atrasadas > 0:
        alertas.append({
            'tipo': 'warning',
            'msg': f"{pgr_atrasadas} plano(s) de ação PGR atrasado(s)",
            'icon': 'fas fa-file-earmark-bar-graph',
        })

    return {
        'total_treinamentos': treinamentos['total_treinamentos'],
        'total_tarefas': tarefas['total_tarefas'],
        'total_entregas_epi': epi['total_entregas'],
        'total_documentos': documentos['total_documentos'],
        'total_pgr_gestao': total_pgr,
        'pgr_gestao_atrasadas': pgr_atrasadas,
        'treinamentos_vencimento_proximo': treinamentos['vencimento_proximo'],
        'tarefas_atrasadas': tarefas['tarefas_atrasadas'],
        'entregas_sem_assinatura': epi['entregas_sem_assinatura'],
        'documentos_a_vencer': documentos['documentos_a_vencer'],
        'alertas_criticos': alertas,
    }

