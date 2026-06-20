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

# suprimentos/permissions.py — aliases de compatibilidade (no FINAL do arquivo)
is_suprimentos = is_comprador          # alias
is_gerente = is_gerencia               # alias

def pode_ver_solicitacao(user):
    """Suprimentos ou Gerência (bloqueia coordenador puro)."""
    return is_comprador(user) or is_gerencia(user)
