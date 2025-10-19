# core/managers.py 

# core/managers.py 
from django.db import models

class FilialQuerySet(models.QuerySet):
    """
    QuerySet customizado com múltiplos métodos de filtragem por filial.
    Contém a lógica DE NEGÓCIO de como os dados devem ser escopados.
    """

    def da_filial(self, filial_obj):
        """
        Filtra o QuerySet para objetos de um objeto Filial específico.
        """
        if filial_obj:
            return self.filter(filial=filial_obj)
        return self.none()

 
    def for_request(self, request):
        """
        Filtra o QuerySet com base no contexto do usuário (request).
        Esta é a lógica de filtragem horizontal principal, movida do
        antigo 'BaseFilialScopedQueryset'.
        """
        user = request.user
        
        # Usuário anônimo não vê nada
        if not user.is_authenticated:
            return self.none()
            
        active_filial_id = request.session.get('active_filial_id')

        # Condição 1: Superuser sem filial na sessão (modo "Deus") vê tudo
        if user.is_superuser and not active_filial_id:
            return self.all()

        # Condição 2: Qualquer usuário com uma filial ativa na sessão
        if active_filial_id:
            return self.filter(filial_id=active_filial_id)

        # Condição 3: Usuário (não superuser) sem filial na sessão:
        # Usa as filiais permitidas do perfil como fallback.
        if not user.is_superuser and hasattr(user, 'filiais_permitidas'):
            # Usa .all() para pegar o queryset de filiais permitidas
            filiais_permitidas = user.filiais_permitidas.all()
            if filiais_permitidas.exists():
                return self.filter(filial__in=filiais_permitidas)
        
        # Condição 4: Se não se encaixar em nada (ex: user sem filiais permitidas)
        # "Nega por padrão" - Retorna um queryset vazio
        return self.none()


class FilialManager(models.Manager):
    """
    Manager que expõe os métodos do FilialQuerySet.
    
    Adicione este manager aos seus modelos:
    objects = FilialManager()
    """
    def get_queryset(self):
        return FilialQuerySet(self.model, using=self._db)

    def da_filial(self, filial_obj):
        """ Exemplo de uso: MeuModelo.objects.da_filial(objeto_filial) """
        return self.get_queryset().da_filial(filial_obj)

    def for_request(self, request):
        """ Exemplo de uso: MeuModelo.objects.for_request(request) """
        return self.get_queryset().for_request(request)
    
    