# core/managers.py

from django.db import models


class FilialQuerySet(models.QuerySet):
    """
    QuerySet que sabe filtrar por filial.
    Funciona com:
      - Models com campo `filial` direto (herdam BaseModel)
      - Models sem campo `filial` que definem `_filial_lookup` (models-filhos)
    """

    def for_request(self, request):
        """
        Filtra pela filial ativa da sessão.
        - Superusuário → SEMPRE vê tudo (acesso irrestrito)
        - Qualquer outro caso → filtra pelo campo/lookup de filial
        """
        user = request.user

        # ✅ Superuser tem acesso irrestrito, sempre
        if user.is_superuser:
            return self

        filial_ativa_id = request.session.get('active_filial_id')

        # Determina o ID da filial a usar
        filial_id = filial_ativa_id
        if not filial_id:
            filial_ativa = getattr(user, 'filial_ativa', None)
            if filial_ativa:
                filial_id = filial_ativa.pk

        # Se tem filial, aplica o filtro
        if filial_id:
            filial_field = self._get_filial_field()
            return self.filter(**{filial_field: filial_id})

        # Sem filial → não vê nada (segurança)
        return self.none()

    def _get_filial_field(self):
        """
        Descobre qual campo usar para filtrar.
        1. Se o model define `_filial_lookup` → usa esse caminho (FK do pai)
        2. Se não → usa 'filial_id' (campo direto)
        """
        model = self.model
        if hasattr(model, '_filial_lookup'):
            return model._filial_lookup
        return 'filial_id'


class FilialManager(models.Manager):
    """
    Manager padrão do sistema.
    Todos os models (com ou sem campo filial direto) podem usá-lo.
    """

    def get_queryset(self):
        return FilialQuerySet(self.model, using=self._db)

    def for_request(self, request):
        return self.get_queryset().for_request(request)

