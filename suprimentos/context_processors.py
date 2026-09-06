# suprimentos/context_processors.py
import logging
from django.core.cache import cache
from django.db.models import Q

from .models import SolicitacaoCompra, Pedido
from . import permissions as perms

logger = logging.getLogger(__name__)

S = SolicitacaoCompra.StatusChoices

# Status que representam "trabalho pendente" por perfil
STATUS_PENDENTES_COMPRADOR = [S.FAZER_COTACAO, S.EM_ENTREGA]
STATUS_PENDENTES_APROVADOR = [S.COTACAO_ENVIADA, S.EM_APROVACAO]
STATUS_ENCERRADOS = [S.FINALIZADO, S.CANCELADO]

CACHE_TTL = 15  # segundos — evita recomputar em navegação rápida


def suprimentos_contadores(request):
    """
    Context processor ÚNICO do módulo Suprimentos.
    Substitui: suprimentos_menu_context, suprimentos_notificacoes, suprimentos_badges.
    Injeta todos os contadores usados no menu lateral / badges / notificações.
    """
    user = request.user
    if not user.is_authenticated:
        return {}

    # Cache por usuário para evitar recálculo em toda navegação
    cache_key = f"suprimentos:contadores:{user.pk}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        is_gerencia = perms.is_gerencia(user)
        is_comprador = perms.is_comprador(user)
        is_aprovador = perms.is_aprovador(user)
        filial_ativa = getattr(user, "filial_ativa", None)

        # ── Base queryset de solicitações "em aberto" ───────────────────
        qs_sol_abertas = SolicitacaoCompra.objects.exclude(
            status__in=STATUS_ENCERRADOS
        )

        if filial_ativa and not (user.is_superuser or is_gerencia):
            qs_sol_abertas = qs_sol_abertas.filter(filial=filial_ativa)

        # ── Pedidos pendentes de aprovação (Gerência) ───────────────────
        count_pedidos_pendentes = 0
        if is_gerencia or user.is_superuser:
            qs_pedidos = Pedido.objects.filter(
                status=Pedido.StatusChoices.PENDENTE
            )
            if filial_ativa:
                qs_pedidos = qs_pedidos.filter(filial=filial_ativa)
            count_pedidos_pendentes = qs_pedidos.count()

        # ── Solicitações pendentes (visão geral) ────────────────────────
        if is_gerencia or user.is_superuser:
            count_sol_pendentes = qs_sol_abertas.count()
        elif is_comprador:
            count_sol_pendentes = qs_sol_abertas.filter(
                Q(comprador=user) | Q(comprador__isnull=True)
            ).count()
        else:
            count_sol_pendentes = 0

        # ── Badges detalhados por etapa ──────────────────────────────────
        badge_cotacao = qs_sol_abertas.filter(status=S.FAZER_COTACAO).count()
        badge_aprovacao = qs_sol_abertas.filter(
            status__in=[S.COTACAO_ENVIADA, S.EM_APROVACAO]
        ).count()
        badge_entrega = qs_sol_abertas.filter(status=S.EM_ENTREGA).count()

        # ── Notificações por perfil (ação requerida) ─────────────────────
        status_acao = []
        if is_comprador:
            status_acao += STATUS_PENDENTES_COMPRADOR
        if is_aprovador:
            status_acao += STATUS_PENDENTES_APROVADOR

        solicitacoes_pendentes_count = (
            qs_sol_abertas.filter(status__in=status_acao).count()
            if status_acao else 0
        )

        ctx = {
            "count_pedidos_pendentes": count_pedidos_pendentes,
            "count_sol_pendentes": count_sol_pendentes,
            "badge_solicitacoes_pendentes": qs_sol_abertas.count(),
            "badge_solicitacoes_cotacao": badge_cotacao,
            "badge_solicitacoes_aprovacao": badge_aprovacao,
            "badge_solicitacoes_entrega": badge_entrega,
            "solicitacoes_pendentes_count": solicitacoes_pendentes_count,
            "is_aprovador_global": is_aprovador,
            "is_comprador_global": is_comprador,
        }

        cache.set(cache_key, ctx, CACHE_TTL)
        return ctx

    except Exception:
        logger.exception(
            "Erro ao calcular contadores do menu Suprimentos (user=%s)",
            getattr(user, "pk", None),
        )
        return {
            "count_pedidos_pendentes": 0,
            "count_sol_pendentes": 0,
            "badge_solicitacoes_pendentes": 0,
            "badge_solicitacoes_cotacao": 0,
            "badge_solicitacoes_aprovacao": 0,
            "badge_solicitacoes_entrega": 0,
            "solicitacoes_pendentes_count": 0,
            "is_aprovador_global": False,
            "is_comprador_global": False,
        }

