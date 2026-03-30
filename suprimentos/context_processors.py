
from django.db.models import Q


def suprimentos_menu_context(request):
    """Injeta contadores no menu lateral do módulo Suprimentos."""
    if not request.user.is_authenticated:
        return {}

    # Só processa se estiver no módulo suprimentos
    if not request.path.startswith('/suprimentos/'):
        return {}

    try:
        from suprimentos.models import Pedido, SolicitacaoCompra

        user = request.user
        ctx = {}

        # Contadores de Pedidos Pendentes
        if user.is_gerente or user.is_administrador or user.is_superuser:
            qs_pedidos = Pedido.objects.filter(status=Pedido.StatusChoices.PENDENTE)
            if hasattr(user, 'filial_ativa') and user.filial_ativa:
                qs_pedidos = qs_pedidos.filter(filial=user.filial_ativa)
            ctx['count_pedidos_pendentes'] = qs_pedidos.count()
        else:
            ctx['count_pedidos_pendentes'] = 0

        # Contadores de Solicitações pendentes (para Compradores e Gerentes)
        if user.is_gerente or user.is_administrador or user.is_superuser:
            qs_sol = SolicitacaoCompra.objects.exclude(
                status__in=['CONCLUIDO', 'CANCELADO']
            )
            if hasattr(user, 'filial_ativa') and user.filial_ativa:
                qs_sol = qs_sol.filter(filial=user.filial_ativa)
            ctx['count_sol_pendentes'] = qs_sol.count()
        elif hasattr(user, 'groups') and user.groups.filter(name='Comprador').exists():
            qs_sol = SolicitacaoCompra.objects.filter(
                Q(comprador=user) | Q(comprador__isnull=True)
            ).exclude(status__in=['CONCLUIDO', 'CANCELADO'])
            ctx['count_sol_pendentes'] = qs_sol.count()
        else:
            ctx['count_sol_pendentes'] = 0

        return ctx

    except Exception:
        return {
            'count_pedidos_pendentes': 0,
            'count_sol_pendentes': 0,
        }

