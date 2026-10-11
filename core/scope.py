
# core/scope.py
def escopo_total(user, perm=None) -> bool:
    """Quem ignora o escopo de técnico."""
    return bool(
        user.is_superuser or user.is_staff or (perm and user.has_perm(perm))
    )

