
# Em core/mixins.py

from django.db.models import Q
from django.contrib.auth.mixins import AccessMixin

class FilialScopedQuerysetMixin:
    """
    Mixin universal para filtrar querysets pela filial ativa na sessão do usuário.
    Compatível com ModelAdmin e Class-Based Views.
    """
    def get_queryset(self, request):
        # =================================================================
        # CORREÇÃO FINAL: A chamada super() NÃO passa o 'request'.
        # Isso a torna compatível com a cadeia de herança da ListView.
        # =================================================================
        qs = super().get_queryset() 
        
        active_filial_id = request.session.get('active_filial_id')

        if request.user.is_superuser and not active_filial_id:
            return qs

        if active_filial_id:
            return qs.filter(filial_id=active_filial_id)
        
        if not request.user.is_superuser:
            # Garante que filiais_permitidas exista no modelo de usuário
            if hasattr(request.user, 'filiais_permitidas'):
                return qs.filter(filial__in=request.user.filiais_permitidas.all())
            # Se não houver, retorna um queryset vazio para segurança
            return qs.none()

        return qs

class TarefaPermissionMixin(AccessMixin):
    """
    Garante que o usuário logado seja o criador ou o responsável pela tarefa.
    Deve ser usado em conjunto com FilialScopedQuerysetMixin.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        # Aplica o filtro de permissão SOBRE a queryset já filtrada pela filial
        return qs.filter(Q(usuario=self.request.user) | Q(responsavel=self.request.user)).distinct()
