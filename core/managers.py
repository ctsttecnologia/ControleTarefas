# Em core/managers.py 

from django.db import models

class FilialQuerySet(models.QuerySet):
    """
    QuerySet customizado que adiciona um método explícito para filtrar por filial.
    """
    def da_filial(self, filial_obj):
        """
        Filtra o QuerySet para objetos pertencentes a uma filial específica.
        Se a filial for None, retorna um queryset vazio por segurança.
        """
        if filial_obj:
            # Assumindo que o campo no modelo se chama 'filial'
            return self.filter(filial=filial_obj)
        return self.none()

class FilialManager(models.Manager):
    """
    Manager que permite chamar o método da_filial diretamente.
    Exemplo: Funcao.objects.da_filial(minha_filial)
    """
    def get_queryset(self):
        return FilialQuerySet(self.model, using=self._db)

    def da_filial(self, filial_obj):
        return self.get_queryset().da_filial(filial_obj)