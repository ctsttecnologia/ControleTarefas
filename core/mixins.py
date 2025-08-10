
# Em core/mixins.py

from django.db.models import Q
from django.contrib.auth.mixins import AccessMixin

class FilialScopedQuerysetMixin(AccessMixin):
    """
    Garante que a queryset da view seja filtrada pela filial ativa na sessão.
    Superusuários sem filial selecionada ("Todas") podem ver tudo.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        active_filial_id = self.request.session.get('active_filial_id')

        if self.request.user.is_superuser and not active_filial_id:
            return qs  # Superuser em modo "Todas as Filiais" vê tudo

        if active_filial_id:
            return qs.filter(filial_id=active_filial_id)

        # Por segurança, se não houver filial ativa, não retorna nada
        return qs.none()

class TarefaPermissionMixin(AccessMixin):
    """
    Garante que o usuário logado seja o criador ou o responsável pela tarefa.
    Deve ser usado em conjunto com FilialScopedQuerysetMixin.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        # Aplica o filtro de permissão SOBRE a queryset já filtrada pela filial
        return qs.filter(Q(usuario=self.request.user) | Q(responsavel=self.request.user)).distinct()
