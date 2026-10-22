# gestao_riscos/mixins.py
# gestao_riscos/mixins.py
from core.mixins import (
    AppPermissionMixin,
    FuncionarioRequiredMixin,
    RequireActiveFilialMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
)


class GestaoRiscosBaseMixin(FuncionarioRequiredMixin, AppPermissionMixin):
    """Auth + vínculo Funcionário + permissão por app (ou granular, se a view definir)."""
    modulo_nome = 'Gestão de Riscos'
    app_label_required = 'gestao_riscos'


class GestaoRiscosWriteMixin(GestaoRiscosBaseMixin, RequireActiveFilialMixin):
    """Escrita: exige filial ativa. Defina `permission_required` na view."""


class GestaoRiscosTecnicoMixin(GestaoRiscosBaseMixin, TecnicoScopeMixin, ViewFilialScopedMixin):
    """CRUD com escopo de técnico + filial. Defina `tecnico_scope_lookup`."""
