# core/managers.py

from django.db import models

class FilialQuerySet(models.QuerySet):
    def for_request(self, request):
        active_filial_id = None
        
        # 1. Tenta obter da sessão primeiro (padrão em aplicações web)
        if hasattr(request, 'session'):
            active_filial_id = request.session.get('active_filial_id')

        # 2. Se não estiver na sessão, tenta obter do objeto de usuário (útil para APIs/testes)
        if not active_filial_id and hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'filial_ativa') and request.user.filial_ativa:
                active_filial_id = request.user.filial_ativa.id
        
        # 3. Se uma ID de filial foi encontrada, filtre por ela.
        if active_filial_id:
            return self.filter(filial_id=active_filial_id)
        
        # 4. (MAIS IMPORTANTE) Se nenhuma filial foi encontrada, NÃO retorne nada.
        #    Isso corrige a falha que mostrava "5 equipamentos".
        return self.none()

class FilialManager(models.Manager):
    def get_queryset(self):
        return FilialQuerySet(self.model, using=self._db)

    def for_request(self, request):
        return self.get_queryset().for_request(request)

