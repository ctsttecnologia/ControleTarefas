
from django.core.exceptions import PermissionDenied
from pgr_gestao.models import PGRDocumento


def validar_acesso_documento(request, pk):
    """
    Valida se o usuário tem acesso ao documento PGR pela filial da sessão.
    Retorna o documento se permitido, senão levanta PermissionDenied.
    """
    # Filtra pela filial (usa o FilialManager)
    documentos_permitidos = PGRDocumento.objects.for_request(request)

    # Se for técnico, restringe mais
    user = request.user
    is_tecnico = user.groups.filter(name='TÉCNICO').exists()
    if is_tecnico:
        documentos_permitidos = documentos_permitidos.filter(criado_por=user)

    try:
        return documentos_permitidos.get(pk=pk)
    except PGRDocumento.DoesNotExist:
        raise PermissionDenied(
            "Você não tem permissão para acessar este documento. "
            "Verifique se a filial correta está selecionada."
        )

