# documentos/utils.py

# documentos/utils.py
from documentos.models import DocumentoAuditLog


def registrar_log_acesso(user, documento, acao, request=None):
    ip = request.META.get('REMOTE_ADDR') if request else None
    DocumentoAuditLog.objects.create(
        documento=documento, usuario=user, acao=acao, ip_address=ip
    )
