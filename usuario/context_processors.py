
# usuario/context_processors.py

def filial_context(request):
    """
    Injeta informações da filial ativa e das filiais permitidas em todos os templates.
    """
    if request.user.is_authenticated:
        filial_ativa = getattr(request.user, 'filial_ativa', None)
        filiais_permitidas = request.user.filiais_permitidas.all()
        
        return {
            'filial_ativa_global': filial_ativa,
            'filiais_permitidas_global': filiais_permitidas,
        }
    return {}
