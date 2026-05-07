
from django import template
from core.mixins import MonitoramentoAccessMixin

register = template.Library()


@register.filter(name='pode_monitorar')
def pode_monitorar(user):
    """Verifica se o usuário pode acessar o painel de monitoramento."""
    return MonitoramentoAccessMixin.user_can_monitor(user)


@register.filter(name='in_grupo')
def in_grupo(user, nome_grupo):
    """Verifica se o usuário pertence a um grupo específico."""
    if not user.is_authenticated:
        return False
    return user.groups.filter(name=nome_grupo).exists()

