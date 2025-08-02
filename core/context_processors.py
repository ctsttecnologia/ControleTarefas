
# core/context_processors.py

from usuario.models import Filial

def filial_context(request):
    """
    Disponibiliza a lista de filiais e a filial ativa para todos os templates.
    """
    if request.user.is_authenticated:
        active_filial_id = request.session.get('active_filial_id')
        active_filial = None
        if active_filial_id:
            try:
                active_filial = Filial.objects.get(pk=active_filial_id)
            except Filial.DoesNotExist:
                pass
        
        return {
            'available_filiais': Filial.objects.all(),
            'active_filial': active_filial,
        }
    return {}
