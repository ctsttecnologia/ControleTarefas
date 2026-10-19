# gestao_riscos/mixins.py

from django.core.checks import messages
from django.core.exceptions import PermissionDenied

from core.mixins import (
    AppPermissionMixin,
    FuncionarioRequiredMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
)
from django.db import IntegrityError, transaction
from core.utils import get_filial_ativa

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


class FilialCreateMixin:
    def form_valid(self, form):
        filial = get_filial_ativa(self.request.user, self.request)
        if filial is None:
            messages.error(self.request, "Nenhuma filial selecionada. Escolha uma no menu superior.")
            raise PermissionDenied("Nenhuma filial selecionada.")
        if hasattr(form.instance, "filial_id"):
            form.instance.filial = filial
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "Já existe um registro com estes dados nesta filial.")
            return self.form_invalid(form)
        if not getattr(self, "success_message", None):
            messages.success(
                self.request,
                f"{self.model._meta.verbose_name.capitalize()} criado(a) com sucesso.",
            )
        return response
