# pgr_gestao/utils/cont_seguranca.py
from django.core.exceptions import PermissionDenied
from pgr_gestao.selectors import documentos_visiveis


def validar_acesso_documento(request, pk):
    try:
        return documentos_visiveis(request).get(pk=pk)
    except Exception:
        raise PermissionDenied(
            "Você não tem permissão para acessar este documento. "
            "Verifique se a filial correta está selecionada.")

