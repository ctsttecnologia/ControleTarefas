
"""
Mixins consolidados do app `pgr_gestao`.

Hierarquia:
    PGRBaseMixin (CBV)
        = FuncionarioRequiredMixin + AppPermissionMixin + SSTPermissionMixin
        + ViewFilialScopedMixin (filtra queryset por filial)

    PGRTecnicoBaseMixin (CBV)
        = PGRBaseMixin + TecnicoScopeMixin (técnico só vê o que criou)

    PGRRequestFormKwargsMixin
        = injeta `request` em form_kwargs (DRY para forms filtrados)

Uso típico:
    - Listas/Detail/Update/Delete com escopo de técnico → PGRTecnicoBaseMixin
    - Listas/Detail/Update/Delete sem escopo de técnico → PGRBaseMixin
    - Creates → PGRBaseMixin + FilialCreateMixin (sem ViewFilialScopedMixin)
"""
from core.mixins import (
    FuncionarioRequiredMixin,
    AppPermissionMixin,
    SSTPermissionMixin,
    ViewFilialScopedMixin,
    TecnicoScopeMixin,
)


class PGRBaseMixin(
    FuncionarioRequiredMixin,
    AppPermissionMixin,
    SSTPermissionMixin,
    ViewFilialScopedMixin,
):
    """
    Mixin base do app pgr_gestao.
    Aplica autenticação + permissões SST + filtro por filial.
    """
    app_label = "pgr_gestao"


class PGRTecnicoBaseMixin(PGRBaseMixin, TecnicoScopeMixin):
    """
    Mixin para views com escopo de técnico.
    O técnico só vê os documentos/registros que ele mesmo criou.

    IMPORTANTE: subclasses DEVEM definir `tecnico_scope_lookup`:
        tecnico_scope_lookup = 'criado_por'
        # ou:
        tecnico_scope_lookup = 'pgr_documento__criado_por'
    """
    pass


class PGRRequestFormKwargsMixin:
    """
    Injeta `self.request` no kwargs do form (DRY).
    Aplica em CreateView/UpdateView cujos forms filtram querysets por filial.
    """
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

