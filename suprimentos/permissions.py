
"""
Permissões customizadas e helpers do app Suprimentos.

Grupos sugeridos (criar via migration de dados ou comando):
- SUP_COORDENADOR  → cria pedidos, vê só os seus
- SUP_COMPRADOR    → vê todos pedidos + gerencia solicitações
- SUP_GERENCIA     → acesso total, inclusive confidenciais
"""
from django.contrib.auth.models import Group


# ───────────── Constantes de Grupos ─────────────
GRUPO_COORDENADOR = "SUP_COORDENADOR"
GRUPO_COMPRADOR = "SUP_COMPRADOR"
GRUPO_SUPRIMENTOS = "SUP_SUPRIMENTOS"
GRUPO_GERENTE = "SUP_GERENTE"


# ───────────── Helpers de Verificação ─────────────
def is_coordenador(user) -> bool:
    return user.groups.filter(name=GRUPO_COORDENADOR).exists()


def is_comprador(user) -> bool:
    return user.groups.filter(name=GRUPO_COMPRADOR).exists()

def is_suprimentos(user) -> bool:
    return user.groups.filter(name=GRUPO_SUPRIMENTOS).exists()

def is_gerente(user) -> bool:
    return user.groups.filter(name=GRUPO_GERENTE).exists()


def pode_ver_solicitacao(user) -> bool:
    """Coordenador NÃO acessa solicitações de compra."""
    return is_comprador(user) or is_gerente(user)


def pode_ver_anexo_pedido(user, anexo) -> bool:
    """Coordenador vê só anexos de seus próprios pedidos."""
    if is_gerente(user) or is_comprador(user):
        return True
    if is_coordenador(user):
        return anexo.pedido.solicitante_id == user.id
    return False


def pode_ver_anexo_solicitacao(user, anexo) -> bool:
    """Anexos de solicitação são bloqueados para coordenador."""
    if anexo.confidencial:
        return is_gerente(user)
    return pode_ver_solicitacao(user)


def pode_baixar_anexo(user, anexo) -> bool:
    """Regra geral: quem vê, pode baixar (exceto confidencial)."""
    from .models import AnexoPedido, AnexoSolicitacao
    if isinstance(anexo, AnexoPedido):
        return pode_ver_anexo_pedido(user, anexo)
    if isinstance(anexo, AnexoSolicitacao):
        return pode_ver_anexo_solicitacao(user, anexo)
    return False

