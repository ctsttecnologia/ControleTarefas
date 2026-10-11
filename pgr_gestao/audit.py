
# pgr_gestao/audit.py
import logging

audit_logger = logging.getLogger("pgr.audit")


def audit(request, action, obj=None, **extra):
    """Sem PII: apenas IDs."""
    filial = getattr(request, "filial_ativa", None)
    partes = {
        "user": request.user.pk,
        "action": action,
        "model": obj._meta.label if obj is not None else None,
        "obj": getattr(obj, "pk", None),
        "filial": getattr(filial, "pk", None),
        "ip": request.META.get("REMOTE_ADDR"),
        **extra,
    }
    audit_logger.info(" ".join(f"{k}={v}" for k, v in partes.items()))


