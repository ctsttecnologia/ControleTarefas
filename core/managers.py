# core/managers.py

from django.db import models

class FilialQuerySet(models.QuerySet):
    """ QuerySet que agora usa o objeto 'request' para uma filtragem inteligente. """
    def for_request(self, request):
        user = request.user

        # Se o usuário não estiver autenticado, não retorna nada.
        if not user.is_authenticated:
            return self.none()

        # Superusuários têm regras especiais
        if user.is_superuser:
            # Verifica se uma filial específica foi selecionada na sessão
            active_filial_id = request.session.get('active_filial_id')
            if active_filial_id:
                return self.filter(filial_id=active_filial_id)
            else:
                # Se nenhuma filial foi selecionada, o superusuário vê tudo.
                return self
        
        # Usuários normais são SEMPRE travados em suas próprias filiais, ignorando a sessão.
        if hasattr(user, 'filial') and user.filial:
            return self.filter(filial=user.filial)
        
        # Se um usuário normal não tem filial, ele não vê nada.
        return self.none()

class FilialManager(models.Manager):
    def get_queryset(self):
        return FilialQuerySet(self.model, using=self._db)

    # Renomeamos o método para refletir que ele precisa do request
    def for_request(self, request):
        return self.get_queryset().for_request(request)

