# suprimentos/permissions.py
def _in_group(user, *names):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=names).exists()

def is_gerencia(user):
    return _in_group(user, "Gerência", "Gerencia", "Admin")

def is_comprador(user):
    return _in_group(user, "Comprador", "Suprimentos")

def is_coordenador(user):
    return _in_group(user, "Coordenador", "Solicitante")
