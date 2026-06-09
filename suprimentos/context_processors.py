
from django.db.models import Q

from .models import SolicitacaoCompra



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

def suprimentos_notificacoes(request):
    """
    Disponibiliza contadores de pendências do módulo suprimentos
    para TODOS os templates (badge no menu).
    """
    if not request.user.is_authenticated:
        return {}
    
    user = request.user
    is_aprovador = user.groups.filter(name='Aprovadores').exists() or user.is_superuser
    is_comprador = user.groups.filter(name='Compradores').exists() or user.is_superuser
    
    # Status que demandam ação do usuário conforme perfil
    status_pendentes = []
    
    if is_comprador:
        status_pendentes += ['FAZER_COTACAO', 'ENTREGA_PENDENTE']
    
    if is_aprovador:
        status_pendentes += ['COTACAO_ENVIADA', 'EM_APROVACAO']
    
    if not status_pendentes:
        return {'solicitacoes_pendentes_count': 0}
    
    count = SolicitacaoCompra.objects.filter(status__in=status_pendentes).count()
    
    return {
        'solicitacoes_pendentes_count': count,
        'is_aprovador_global': is_aprovador,
        'is_comprador_global': is_comprador,
    }

def suprimentos_badges(request):
    """Disponibiliza contadores de Solicitações pendentes no menu lateral."""
    if not request.user.is_authenticated:
        return {}
    
    qs = SolicitacaoCompra.objects.exclude(status__in=['CONCLUIDO', 'CANCELADO'])
    
    if not request.user.is_superuser and not request.user.groups.filter(name='APROVADORES').exists():
        filial = getattr(request.user, 'filial_ativa', None)
        if filial:
            qs = qs.filter(contrato__filial=filial)
    
    return {
        'badge_solicitacoes_pendentes': qs.count(),
        'badge_solicitacoes_cotacao': qs.filter(status='FAZER_COTACAO').count(),
        'badge_solicitacoes_aprovacao': qs.filter(
            status__in=['COTACAO_ENVIADA', 'EM_APROVACAO']
        ).count(),
    }