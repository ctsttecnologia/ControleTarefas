# pgr_gestao/mixins.py

from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db import models
from django.http import HttpResponseRedirect
from core.mixins import (
    FuncionarioRequiredMixin, AppPermissionMixin
    ,
    ViewFilialScopedMixin, TecnicoScopeMixin
)
from .audit import audit

class PGRRequestFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs
    
class PGRBaseMixin(FuncionarioRequiredMixin, AppPermissionMixin,
                   ViewFilialScopedMixin, PGRRequestFormKwargsMixin):
    app_label_required = "pgr_gestao"  # antes: app_label (ignorado)


class PGRTecnicoBaseMixin(PGRBaseMixin, TecnicoScopeMixin):
    """Use também em Update/Delete. Defina tecnico_scope_lookup."""

class PGRRequestFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

class PGRAuditMixin:
    audit_action = None

    def form_valid(self, form):
        response = super().form_valid(form)
        audit(self.request, self.audit_action or type(self).__name__,
              getattr(self, "object", None))
        return response


class PGRSoftDeleteMixin:
    """DeleteView com exclusão lógica (Django >= 4 usa form_valid)."""
    def form_valid(self, form):
        obj = self.object = self.get_object()
        obj.soft_delete(user=self.request.user)
        audit(self.request, "soft_delete", obj)
        messages.success(
            self.request, f"{obj._meta.verbose_name.capitalize()} excluído(a) com sucesso."
        )
        return HttpResponseRedirect(self.get_success_url())


class FilialConsistencyMixin(models.Model):
    """
    FILIAL_PARENT:  FK do pai que define a filial (copiada no save).
    FILIAL_RELATED: FKs que precisam estar na MESMA filial.
    """
    FILIAL_PARENT = None
    FILIAL_RELATED = ()

    class Meta:
        abstract = True

    def _filial_esperada_id(self):
        if self.FILIAL_PARENT:
            pai = getattr(self, self.FILIAL_PARENT, None)
            return getattr(pai, "filial_id", None)
        return self.filial_id

    def clean(self):
        super().clean()
        esperado = self._filial_esperada_id()
        if not esperado:
            return
        erros = {}
        for nome in self.FILIAL_RELATED:
            if getattr(self, f"{nome}_id", None) is None:
                continue
            outro = getattr(self, nome)
            if getattr(outro, "filial_id", esperado) != esperado:
                erros[nome] = "Este registro pertence a outra filial."
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        esperado = self._filial_esperada_id()
        if self.FILIAL_PARENT and esperado:
            self.filial_id = esperado
        super().save(*args, **kwargs)