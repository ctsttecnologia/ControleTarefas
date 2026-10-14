from django.db.models import Q
from django.utils import timezone

PERM_VIEW_ALL = 'tarefas.view_all_tarefas'
PERM_VIEW_GROUP = 'tarefas.view_group_tarefas'
PERM_CHANGE = 'tarefas.change_tarefas'
PERM_EXPORT = 'tarefas.export_tarefas'
PERM_EQUIPE = 'tarefas.view_desempenho_equipe'
STATUS_ENCERRADOS = 'concluida', 'cancelada'


def is_criador(user, tarefa):
    return tarefa.usuario_id == user.pk

def is_responsavel(user, tarefa):
    return tarefa.responsavel_id == user.pk


def is_participante(user, tarefa):
    return tarefa.participantes.filter(pk=user.pk).exists()


def is_grupo_da_tarefa(user, tarefa):
    if not user.has_perm(PERM_VIEW_GROUP):
        return False

    return tarefa.grupos_com_acesso.filter(
        pk__in=user.groups.values('pk')
    ).exists()


def can_view_all(user):
    return user.is_superuser or user.has_perm(PERM_VIEW_ALL)


def can_view(user, tarefa):
    return (
        can_view_all(user)
        or is_responsavel(user, tarefa)
        or is_participante(user, tarefa)
        or is_grupo_da_tarefa(user, tarefa)
    )


def can_edit(user, tarefa):
    return (
        user.is_superuser
        or user.has_perm(PERM_CHANGE)
        or tarefa.usuario_id == user.pk
        or is_responsavel(user, tarefa)
    )


def can_conclude(user, tarefa):
    return (
        user.is_superuser
        or tarefa.usuario_id == user.pk
        or is_responsavel(user, tarefa)
    )


def can_delete(user, tarefa):
    return user.is_superuser or tarefa.usuario_id == user.pk


def can_comment(user, tarefa):
    return can_view(user, tarefa)


def can_change_status(user, tarefa, novo_status):
    if novo_status == 'concluida' or tarefa.status == 'concluida':
        return can_conclude(user, tarefa)
    return can_edit(user, tarefa)


def esta_atrasada(tarefa, agora=None):
    """
    Regra única de atraso: prazo já passou e a tarefa não está encerrada.
    Vale para qualquer status não encerrado, inclusive 'programada'.
    """
    if not tarefa.prazo:
        return False
    agora = agora or timezone.now()
    return tarefa.prazo < agora and tarefa.status not in STATUS_ENCERRADOS

def filtrar_por_filial(queryset, request):
    """
    Filtra sempre pela filial ativa.
    Usuário comum sem filial válida não vê tarefas.
    Superusuário sem filial ativa pode ver todas as filiais.
    """
    filial_id = request.session.get('active_filial_id')

    if filial_id:
        if request.user.is_superuser:
            return queryset.filter(filial_id=filial_id)

        # Não confia apenas no valor da sessão: valida o vínculo do usuário.
        if request.user.filiais_permitidas.filter(pk=filial_id).exists():
            return queryset.filter(filial_id=filial_id)

        return queryset.none()

    return queryset if request.user.is_superuser else queryset.none()


def filtrar_visibilidade(queryset, user, request=None):
    qs = queryset
    if request is not None:
        qs = filtrar_por_filial(qs, request)

    if can_view_all(user):
        return qs.distinct()

    filtro = Q(usuario=user) | Q(responsavel=user) | Q(participantes=user)
    if user.has_perm(PERM_VIEW_GROUP):
        filtro |= Q(grupos_com_acesso__in=user.groups.all())

    return qs.filter(filtro).distinct()

