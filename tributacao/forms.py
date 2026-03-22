
# tributacao/forms.py

from django import forms
from .models import NCM, CFOP, CST, GrupoTributario, TributacaoFederal, TributacaoEstadual


# ══════════════════════════════════════════════════════
# MIXIN — Classes CSS padrão Bootstrap
# ══════════════════════════════════════════════════════
class BootstrapFormMixin:
    """Aplica classes Bootstrap a todos os campos do form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")

            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = f"form-check-input {existing}".strip()
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = f"form-select {existing}".strip()
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs["class"] = f"form-control {existing}".strip()
                field.widget.attrs.setdefault("rows", 3)
            else:
                field.widget.attrs["class"] = f"form-control {existing}".strip()


# ══════════════════════════════════════════════════════
# NCM
# ══════════════════════════════════════════════════════
class NCMForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = NCM
        fields = ["codigo", "descricao", "ex_tipi", "aliquota_ipi_padrao", "ativo"]
        widgets = {
            "codigo": forms.TextInput(attrs={"placeholder": "0000.00.00"}),
        }


# ══════════════════════════════════════════════════════
# CFOP
# ══════════════════════════════════════════════════════
class CFOPForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CFOP
        fields = ["codigo", "descricao", "tipo", "aplicacao", "ativo"]
        widgets = {
            "codigo": forms.TextInput(attrs={"placeholder": "0000", "maxlength": 4}),
        }


# ══════════════════════════════════════════════════════
# CST
# ══════════════════════════════════════════════════════
class CSTForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CST
        fields = ["tipo", "codigo", "descricao"]
        widgets = {
            "codigo": forms.TextInput(attrs={"placeholder": "00", "maxlength": 3}),
        }


# ══════════════════════════════════════════════════════
# GRUPO TRIBUTÁRIO
# ══════════════════════════════════════════════════════
class GrupoTributarioForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = GrupoTributario
        fields = ["nome", "descricao", "natureza", "cfop", "ncm", "filial", "ativo"]


# ══════════════════════════════════════════════════════
# TRIBUTAÇÃO FEDERAL
# ══════════════════════════════════════════════════════
class TributacaoFederalForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TributacaoFederal
        fields = [
            "cst_ipi", "aliquota_ipi",
            "cst_pis", "aliquota_pis", "gera_credito_pis",
            "cst_cofins", "aliquota_cofins", "gera_credito_cofins",
            "observacoes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar CSTs por tipo
        self.fields["cst_ipi"].queryset = CST.objects.filter(tipo__startswith="IPI")
        self.fields["cst_pis"].queryset = CST.objects.filter(tipo="PIS")
        self.fields["cst_cofins"].queryset = CST.objects.filter(tipo="COFINS")


# ══════════════════════════════════════════════════════
# TRIBUTAÇÃO ESTADUAL
# ══════════════════════════════════════════════════════
class TributacaoEstadualForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TributacaoEstadual
        fields = [
            "uf_origem", "uf_destino",
            "cst_icms", "aliquota_icms", "reducao_base_icms", "permite_credito",
            "tem_st", "mva", "aliquota_icms_st",
            "aliquota_fcp",
            "ativo", "observacoes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cst_icms"].queryset = CST.objects.filter(tipo="ICMS")


# ══════════════════════════════════════════════════════
# FORMSETS — Para inlines na interface
# ══════════════════════════════════════════════════════
TributacaoEstadualFormSet = forms.inlineformset_factory(
    GrupoTributario,
    TributacaoEstadual,
    form=TributacaoEstadualForm,
    extra=1,
    can_delete=True,
)

