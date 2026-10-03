
# tarefas/permissions.py
from django.db.models import Q

PERM_VIEW_ALL = 'tarefas.view_all_tarefas'
PERM_CHANGE   = 'tarefas.change_tarefas'
PERM_EXPORT   = 'tarefas.export_tarefas'
PERM_EQUIPE   = 'tarefas.view_desempenho_equipe'


def is_criador(user, t):
    return t.usuario_id == user.pk

def is_responsavel(user, t):
    return t.responsavel_id == user.pk

def is_participante(user, t):
    return t.participantes.filter(pk=user.pk).exists()


def can_view_all(user):
    """view_all OU change enxergam todas as tarefas (da filial ativa)."""
    return (user.is_superuser
            or user.has_perm(PERM_VIEW_ALL)
            or user.has_perm(PERM_CHANGE))

def can_view(user, t):
    return (can_view_all(user) or is_criador(user, t)
            or is_responsavel(user, t) or is_participante(user, t))

def can_edit(user, t):
    return (user.is_superuser or user.has_perm(PERM_CHANGE)
            or is_criador(user, t) or is_responsavel(user, t))

def can_conclude(user, t):
    return user.is_superuser or is_criador(user, t) or is_responsavel(user, t)

def can_delete(user, t):
    return user.is_superuser or is_criador(user, t)

def can_comment(user, t):
    return can_view(user, t)

def can_change_status(user, t, novo_status):
    """Entrar ou sair de 'concluida' exige can_conclude; demais status exigem can_edit."""
    if novo_status == 'concluida' or t.status == 'concluida':
        return can_conclude(user, t)
    return can_edit(user, t)


def filtrar_por_filial(qs, request):
    """Falha fechado: sem filial ativa, só superuser vê tudo."""
    filial_id = request.session.get('active_filial_id')
    if filial_id:
        return qs.filter(filial_id=filial_id)
    return qs if request.user.is_superuser else qs.none()


def filtrar_visibilidade(qs, user):
    if can_view_all(user):
        return qs
    return qs.filter(
        Q(responsavel=user) | Q(participantes=user) | Q(usuario=user)
    ).distinct()

