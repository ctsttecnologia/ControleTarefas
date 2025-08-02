# core/admin.py

from django.contrib import admin

class FilialAdminMixin(admin.ModelAdmin):
    """
    Mixin para o Admin que filtra os dados pela filial do usuário
    e preenche a filial automaticamente ao criar um novo objeto.
    """
    def get_queryset(self, request):
        # Pega a queryset padrão
        qs = super().get_queryset(request)
        
        # Se o usuário não for superuser, filtra pela sua filial
        if request.user.is_superuser:
            return qs
        
        if hasattr(request.user, 'filial') and request.user.filial:
            return qs.filter(filial=request.user.filial)
        
        # Se não for superuser e não tiver filial, não mostra nada.
        return qs.none()

    def save_model(self, request, obj, form, change):
        # Se um objeto está sendo criado (não alterado) e não tem filial definida...
        if not change and not getattr(obj, 'filial_id', None):
            # ...e o usuário não é superuser, atribui a filial do usuário.
            if not request.user.is_superuser:
                obj.filial = request.user.filial
        super().save_model(request, obj, form, change)