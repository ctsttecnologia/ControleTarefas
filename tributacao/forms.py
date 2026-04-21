
# tributacao/forms.py

from django import forms
from core.validators import SecureFileValidator
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
            elif isinstance(field.widget, forms.FileInput):
                # FileInput e ClearableFileInput recebem form-control também
                field.widget.attrs["class"] = f"form-control {existing}".strip()
            else:
                field.widget.attrs["class"] = f"form-control {existing}".strip()


# ══════════════════════════════════════════════════════
# NCM
# ══════════════════════════════════════════════════════
class NCMForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = NCM
        fields = [
            "codigo", "descricao", "ex_tipi",
            "aliquota_ipi_padrao",
            "arquivo_xml",   # ← campo de upload seguro
            "ativo",
        ]
        widgets = {
            "codigo": forms.TextInput(attrs={"placeholder": "0000.00.00"}),
        }

    def clean_arquivo_xml(self):
        arquivo = self.cleaned_data.get("arquivo_xml")
        # Só valida se um novo arquivo foi enviado
        # (arquivo pode ser False = "limpar", ou None = sem alteração)
        if arquivo and hasattr(arquivo, "name"):
            SecureFileValidator("tributacao")(arquivo)
        return arquivo


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
class GrupoTributarioForm(forms.ModelForm):
    class Meta:
        model = GrupoTributario
        fields = ['nome', 'descricao', 'natureza', 'cfop', 'ncm', 'filial', 'ativo']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not (user.is_superuser or user.has_perm('tributacao.pode_gerenciar_todas_filiais')):
            # Restringe filiais no dropdown
            filial_ativa = getattr(user, 'filial_ativa', None)
            if filial_ativa:
                self.fields['filial'].queryset = self.fields['filial'].queryset.filter(
                    pk=filial_ativa.pk
                )
                self.fields['filial'].initial = filial_ativa
                self.fields['filial'].disabled = True  # bloqueia alteração
            else:
                self.fields['filial'].queryset = self.fields['filial'].queryset.none()
                self.fields['filial'].initial = None
                self.fields['filial'].disabled = True  # bloqueia alteração 
                
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
            "documento_fiscal",  # ← campo de upload seguro
            "observacoes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra CSTs por tipo
        self.fields["cst_ipi"].queryset    = CST.objects.filter(tipo__startswith="IPI")
        self.fields["cst_pis"].queryset    = CST.objects.filter(tipo="PIS")
        self.fields["cst_cofins"].queryset = CST.objects.filter(tipo="COFINS")

    def clean_documento_fiscal(self):
        arquivo = self.cleaned_data.get("documento_fiscal")
        # Só valida se um novo arquivo foi enviado
        if arquivo and hasattr(arquivo, "name"):
            SecureFileValidator("tributacao")(arquivo)
        return arquivo


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

    def clean(self):
        cleaned = super().clean()
        tem_st = cleaned.get("tem_st")
        mva    = cleaned.get("mva")

        # Alerta coerência: MVA preenchido sem ST ativo
        if mva and mva > 0 and not tem_st:
            self.add_error(
                "tem_st",
                'MVA preenchido mas "Tem ICMS-ST?" está desmarcado.'
            )

        return cleaned


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

