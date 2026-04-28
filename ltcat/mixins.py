
# ltcat/mixins.py
"""
Mixins consolidados do app LTCAT.

Hierarquia:
    LTCATBaseMixin
        - FuncionarioRequiredMixin (auth + vinculo)
        - AppPermissionMixin       (permissao do app)
        - SSTPermissionMixin       (permissao Django granular)

    LTCATChildMixin
        - LTCATBaseMixin
        - LTCATAccessMixin (verificacao por filial do documento pai)

Helpers:
    LTCATAccessMixin       -> valida acesso por filial em LTCATDocumento
    FilialFormKwargsMixin  -> injeta Filial ativa em form_kwargs
"""

from django.http import Http404
from django.shortcuts import get_object_or_404

from core.mixins import (
    AppPermissionMixin,
    FuncionarioRequiredMixin,
    SSTPermissionMixin,
)


# =============================================================================
# == MIXIN BASE DO APP
# =============================================================================

class LTCATBaseMixin(
    FuncionarioRequiredMixin,
    AppPermissionMixin,
    SSTPermissionMixin,
):
    """
    Mixin base do app LTCAT.

    Stack de seguranca:
      1. FuncionarioRequiredMixin -> auth + vinculo Funcionario
      2. AppPermissionMixin       -> permissao do app (ltcat)
      3. SSTPermissionMixin       -> permissao Django granular (NIVEL 1)

    As views filhas continuam definindo 'permission_required' normalmente,
    pois SSTPermissionMixin herda de PermissionRequiredMixin.
    """
    modulo_nome = 'LTCAT'
    app_label_required = 'ltcat'


# =============================================================================
# == MIXIN AUXILIAR (verificacao por filial do documento)
# =============================================================================

class LTCATAccessMixin:
    """
    Verifica se o usuario pode acessar um LTCAT especifico.
    Superuser/staff veem tudo; demais so da propria filial (via sessao).
    """

    def check_ltcat_access(self, ltcat_doc):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return True
        filial_id = self.request.session.get("active_filial_id")
        return bool(filial_id) and ltcat_doc.filial_id == int(filial_id)


# =============================================================================
# == HELPER: injecao de Filial em form_kwargs
# =============================================================================

class FilialFormKwargsMixin:
    """
    Injeta a Filial ativa (sessao) no form via get_form_kwargs.
    Elimina a repeticao do mesmo bloco em todas as Create/UpdateView.
    """

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        filial_id = self.request.session.get("active_filial_id")
        if filial_id:
            from usuario.models import Filial
            try:
                kwargs["filial"] = Filial.objects.get(pk=filial_id)
            except Filial.DoesNotExist:
                kwargs["filial"] = None
        return kwargs


# =============================================================================
# == MIXIN PARA RECURSOS-FILHO DO LTCAT
# =============================================================================

class LTCATChildMixin(LTCATBaseMixin, LTCATAccessMixin):
    """
    Mixin para views de itens-filho do documento LTCAT
    (Revisoes, Funcoes, Riscos, Conclusoes, Recomendacoes, Anexos, etc).

    - Garante toda a stack de seguranca (LTCATBaseMixin)
    - Verifica acesso ao LTCAT pai por filial (LTCATAccessMixin)
    - Resolve self.get_ltcat() a partir de kwargs['ltcat_pk']
    - Injeta 'ltcat' no contexto do template
    """

    def get_ltcat(self):
        from .models import LTCATDocumento
        ltcat_doc = get_object_or_404(LTCATDocumento, pk=self.kwargs["ltcat_pk"])
        if not self.check_ltcat_access(ltcat_doc):
            raise Http404("LTCAT nao encontrado.")
        return ltcat_doc

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ltcat"] = self.get_ltcat()
        return ctx


