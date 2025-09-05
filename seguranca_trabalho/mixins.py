
from django.contrib.auth.mixins import PermissionRequiredMixin

class SSTPermissionMixin(PermissionRequiredMixin):
    permission_required = 'seguranca_trabalho.view_equipamento'
    raise_exception = True
