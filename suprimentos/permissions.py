# suprimentos/permissions.py

# Nomes canônicos de grupos — usar SEMPRE estas constantes, nunca strings soltas
GRUPO_GERENCIA = ["Gerência", "Gerencia", "Admin"]
GRUPO_COMPRADOR = ["Comprador", "Suprimentos", "Compradores"]
GRUPO_COORDENADOR = ["Coordenador", "Solicitante"]
GRUPO_APROVADORES = ["Aprovadores"]


def _in_group(user, *names):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=names).exists()


def is_gerencia(user):
    return _in_group(user, *GRUPO_GERENCIA)

def is_comprador(user):
    return _in_group(user, *GRUPO_COMPRADOR)

def is_coordenador(user):
    return _in_group(user, *GRUPO_COORDENADOR)

def is_aprovador(user):
    return _in_group(user, *GRUPO_APROVADORES) or is_gerencia(user)


is_suprimentos = is_comprador
is_gerente = is_gerencia

def pode_ver_solicitacao(user):
    return is_comprador(user) or is_gerencia(user)

