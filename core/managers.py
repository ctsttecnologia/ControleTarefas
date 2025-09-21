# core/managers.py 

from django.db import models

class FilialQuerySet(models.QuerySet):
    """
    QuerySet customizado com múltiplos métodos de filtragem por filial.
    """
    # SEU MÉTODO EXISTENTE (MANTIDO)
    def da_filial(self, filial_obj):
        """
        Filtra o QuerySet para objetos de um objeto Filial específico.
        """
        if filial_obj:
            # Assumindo que o campo no modelo se chama 'filial'
            return self.filter(filial=filial_obj)
        return self.none()

    # NOVO MÉTODO ADICIONADO
    def for_request(self, request):
        """
        Filtra o QuerySet com base na filial ativa na sessão da requisição (request).
        """
        active_filial_id = request.session.get('active_filial_id')
        if not active_filial_id:
            return self.none()
        # Filtra diretamente pelo ID da filial, o que é mais eficiente
        return self.filter(filial_id=active_filial_id)


class FilialManager(models.Manager):
    """
    Manager que expõe os métodos do FilialQuerySet.
    """
    def get_queryset(self):
        return FilialQuerySet(self.model, using=self._db)

    # SEU MÉTODO EXISTENTE (MANTIDO)
    def da_filial(self, filial_obj):
        """ Exemplo de uso: MeuModelo.objects.da_filial(objeto_filial) """
        return self.get_queryset().da_filial(filial_obj)

    # NOVO MÉTODO ADICIONADO
    def for_request(self, request):
        """ Exemplo de uso: MeuModelo.objects.for_request(request) """
        return self.get_queryset().for_request(request)