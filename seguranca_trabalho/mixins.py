# gestao_riscos/mixins.py

from core.mixins import (
    AppPermissionMixin,
    FuncionarioRequiredMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
)


# =============================================================================
# == MIXIN BASE DO APP (camada de seguranca consolidada)
# =============================================================================

class GestaoRiscosBaseMixin(FuncionarioRequiredMixin, AppPermissionMixin):
    """
    Mixin base do app Gestao de Riscos.

    Consolida a stack de seguranca padrao do projeto:
      1. FuncionarioRequiredMixin -> autenticacao + vinculo com Funcionario
      2. AppPermissionMixin       -> permissao por app (gestao_riscos)

    NAO inclui ViewFilialScopedMixin nem TecnicoScopeMixin porque essas
    camadas dependem do model e variam por view. Use GestaoRiscosTecnicoMixin
    para o combo completo (CRUD com escopo de tecnico + filial).

    Uso tipico:
        class CalendarioView(GestaoRiscosBaseMixin, TemplateView):
            template_name = 'gestao_riscos/calendario.html'
    """
    modulo_nome = 'Gestao de Riscos'
    app_label_required = 'gestao_riscos'


# =============================================================================
# == MIXIN COMPOSTO (combo padrao de CRUD com escopo)
# =============================================================================

class GestaoRiscosTecnicoMixin(
    GestaoRiscosBaseMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
):
    """
    Mixin composto para views de CRUD com escopo completo.

    Combina:
      1. GestaoRiscosBaseMixin   -> Auth + Funcionario + AppPermission
      2. TecnicoScopeMixin       -> Limita ao tecnico logado (se aplicavel)
      3. ViewFilialScopedMixin   -> Filtra por filial ativa (multi-tenant)

    Use quando a view manipula recursos vinculados a um tecnico responsavel
    (Inspecao, CartaoTag, etc.). Defina 'tecnico_scope_lookup' na view filha.

    Uso tipico:
        class CartaoTagListView(GestaoRiscosTecnicoMixin, ListView):
            model = CartaoTag
            tecnico_scope_lookup = 'responsavel'
    """
    pass

