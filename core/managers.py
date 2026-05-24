# core/managers.py

from django.db import models
from .middleware import get_current_filial
from core.utils import get_filial_ativa


class FilialQuerySet(models.QuerySet):
    """
    QuerySet que sabe filtrar por filial.
    Funciona com:
      - Models com campo `filial` direto (herdam BaseModel)
      - Models sem campo `filial` que definem `_filial_lookup` (models-filhos)
    """

    def for_request(self, request):
        """Filtra pelo escopo da filial ativa do request."""
        if request is None:
            return self.none()
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()

        # Superuser vê tudo (opcional — remova se não quiser esse comportamento)
        if getattr(user, "is_superuser", False):
            return self

        filial = get_filial_ativa(user, request)
        if filial is None:
            return self.none()

        lookup = self._get_filial_field()
        # filial_id aceita o objeto direto também
        return self.filter(**{lookup: filial})

    def _get_filial_field(self):
        """
        Descobre qual campo usar para filtrar.
        1. Se o model define `_filial_lookup` -> usa esse caminho (FK do pai)
        2. Se não -> usa 'filial_id' (campo direto)
        """
        model = self.model
        if hasattr(model, '_filial_lookup'):
            return model._filial_lookup
        return 'filial_id'


class FilialManager(models.Manager.from_queryset(FilialQuerySet)):
    """
    Manager que:
      - Aplica filtro automático por filial via thread-local (middleware)
      - Expõe todos os métodos do FilialQuerySet (incluindo `for_request`)
    """

    def get_queryset(self):
        qs = super().get_queryset()  # já é FilialQuerySet
        filial = get_current_filial()
        if filial is not None:
            lookup = qs._get_filial_field()
            return qs.filter(**{lookup: filial})
        return qs

    def all_filiais(self):
        """Retorna o queryset SEM filtrar por filial (bypassa o thread-local)."""
        return FilialQuerySet(self.model, using=self._db)


