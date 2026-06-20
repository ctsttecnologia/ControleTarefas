
# suprimentos/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import (
    Parceiro, Material, Contrato,
    Pedido, ItemPedido,
    SolicitacaoCompra, ItemSolicitacao, Cotacao,
    PedidoCompra, ItemPedidoCompra,
)
from decimal import Decimal
from django.forms import formset_factory, inlineformset_factory
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import VerbaContrato


# ═════════════════════════════════════════════════════════════
# MIXIN — aplica classes Bootstrap automaticamente
# ═════════════════════════════════════════════════════════════
class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


# ═════════════════════════════════════════════════════════════
# CADASTROS AUXILIARES
# ═════════════════════════════════════════════════════════════
class ParceiroForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Parceiro
        fields = [
            "razao_social", "nome_fantasia", "cnpj", "inscricao_estadual",
            "contato", "telefone", "celular", "email", "site",
            "endereco", "observacoes",
            "eh_fabricante", "eh_fornecedor", "ativo", "filial",
        ]
        widgets = {
            "endereco": forms.Textarea(attrs={"rows": 2}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class MaterialForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Material
        fields = [
            "codigo", "descricao", "classificacao", "tipo", "marca",
            "unidade", "valor_unitario", "equipamento_epi", "ferramenta_ref",
            "ncm", "grupo_tributario", "filial", "ativo",
        ]


class ContratoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ["cm", "cliente", "filial", "ativo"]


# ═════════════════════════════════════════════════════════════
# 1. PEDIDO + ITENS
# ═════════════════════════════════════════════════════════════
class PedidoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Pedido
        fields = [
            "contrato", "filial", "tipo_obra",
            "data_necessaria", "observacao",
        ]
        widgets = {
            "data_necessaria": forms.DateInput(attrs={"type": "date"}),
            "observacao": forms.Textarea(attrs={"rows": 3}),
        }


class ItemPedidoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ItemPedido
        fields = [
            "material", "quantidade", "unidade_medida",
            "valor_unitario", "observacao",
        ]
        widgets = {
            "observacao": forms.Textarea(attrs={"rows": 1}),
        }


ItemPedidoFormSet = inlineformset_factory(
    Pedido, ItemPedido,
    form=ItemPedidoForm,
    extra=1,
    can_delete=True,
)


# ═════════════════════════════════════════════════════════════
# 2. APROVAR PEDIDO (não-ModelForm — decisão livre)
# ═════════════════════════════════════════════════════════════
class AprovarPedidoForm(forms.Form):
    DECISOES = [
        ("APROVAR", "Aprovar"),
        ("REVISAR", "Devolver para revisão"),
        ("REPROVAR", "Reprovar"),
    ]
    decisao = forms.ChoiceField(
        choices=DECISOES,
        widget=forms.RadioSelect,
        label="Decisão",
    )
    motivo = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        label="Motivo (obrigatório se revisar/reprovar)",
    )

    def clean(self):
        cleaned = super().clean()
        decisao = cleaned.get("decisao")
        motivo = cleaned.get("motivo")
        if decisao in ("REVISAR", "REPROVAR") and not motivo:
            self.add_error("motivo", "Informe o motivo para revisar ou reprovar.")
        return cleaned


# ═════════════════════════════════════════════════════════════
# 3. COTAÇÃO (NxN por item)
# ═════════════════════════════════════════════════════════════

class CotacaoCabecalhoForm(forms.Form):
    """Dados COMUNS do fornecedor — aplicados a todos os itens cotados."""
    fornecedor = forms.ModelChoiceField(
        queryset=Parceiro.objects.filter(eh_fornecedor=True, ativo=True),
        label="Fornecedor",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    condicoes_pagamento = forms.CharField(
        label="Condições de Pagamento", required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    prazo_entrega_dias = forms.IntegerField(
        label="Prazo de Entrega (dias)", required=False, min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    validade_cotacao = forms.DateField(
        label="Validade da Cotação", required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    observacoes = forms.CharField(
        label="Observações", required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
    anexo_cotacao = forms.FileField(
        label="Anexo (PDF da cotação)", required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )


class CotacaoItemValorForm(forms.Form):
    """Uma linha: o valor unitário que o fornecedor deu para CADA item."""
    item_id = forms.IntegerField(widget=forms.HiddenInput())
    valor_unitario = forms.DecimalField(
        label="Valor Unitário", required=False,
        max_digits=12, decimal_places=2, min_value=Decimal("0.00"),
        widget=forms.NumberInput(attrs={
            "class": "form-control valor-item",
            "step": "0.01", "placeholder": "0,00",
        }),
    )


CotacaoItemValorFormSet = formset_factory(CotacaoItemValorForm, extra=0)

class CotacaoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Cotacao
        fields = [
            "fornecedor", "valor_unitario", "prazo_entrega_dias",
            "condicoes_pagamento", "validade_cotacao",
            "observacoes", "anexo_cotacao",
        ]
        widgets = {
            "validade_cotacao": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
            "anexo_cotacao": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "application/pdf",
            }),
        }

    def __init__(self, *args, solicitacao=None, item=None, **kwargs):
        self.solicitacao = solicitacao
        self.item = item
        super().__init__(*args, **kwargs)
        # Só fornecedores ativos
        self.fields["fornecedor"].queryset = Parceiro.objects.filter(
            eh_fornecedor=True, ativo=True
        )

    def clean(self):
        cleaned = super().clean()
        fornecedor = cleaned.get("fornecedor")
        if self.item and fornecedor:
            if Cotacao.objects.filter(item_solicitacao=self.item, fornecedor=fornecedor).exists():
                self.add_error(
                    "fornecedor",
                    "Este fornecedor já cotou este item. Edite a cotação existente."
                )
        return cleaned

class AprovarItemCotacaoForm(forms.Form):
    """Placeholder — a escolha por item é tratada na view via POST manual."""
    pass

# ═════════════════════════════════════════════════════════════
# WIDGET / FIELD PARA MÚLTIPLOS ARQUIVOS (Django < 5.0 compatível)
# ═════════════════════════════════════════════════════════════
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={
            "class": "form-control",
            "multiple": True,
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, (list, tuple)):
            return [single(d, initial) for d in data]
        return [single(data, initial)]


# ═════════════════════════════════════════════════════════════
# 4. PEDIDO DE COMPRA + ITENS + ENTREGA
# ═════════════════════════════════════════════════════════════
class PedidoCompraForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PedidoCompra
        fields = [
            "fornecedor", "filial", "data_emissao",
            "data_entrega_prevista", "observacoes",
        ]
        widgets = {
            "data_emissao": forms.DateInput(attrs={"type": "date"}),
            "data_entrega_prevista": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned = super().clean()
        emissao = cleaned.get("data_emissao")
        entrega = cleaned.get("data_entrega_prevista")
        if emissao and entrega and entrega < emissao:
            self.add_error(
                "data_entrega_prevista",
                "A data de entrega prevista não pode ser anterior à emissão.",
            )
        return cleaned


class ItemPedidoCompraForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ItemPedidoCompra
        fields = ["material", "quantidade", "valor_unitario", "observacao"]

    def clean_quantidade(self):
        qtd = self.cleaned_data.get("quantidade")
        if qtd is not None and qtd <= 0:
            raise forms.ValidationError("A quantidade deve ser maior que zero.")
        return qtd

    def clean_valor_unitario(self):
        valor = self.cleaned_data.get("valor_unitario")
        if valor is not None and valor < 0:
            raise forms.ValidationError("O valor unitário não pode ser negativo.")
        return valor


# Formset inline para os itens do pedido
ItemPedidoCompraFormSet = inlineformset_factory(
    PedidoCompra,
    ItemPedidoCompra,
    form=ItemPedidoCompraForm,
    extra=1,
    can_delete=True,
)


class EntregaPedidoCompraForm(BootstrapMixin, forms.ModelForm):
    """Acompanhamento de entrega / NF do Pedido de Compra."""
    anexos = MultipleFileField(
        required=False,
        label="Anexos / Notas Fiscais",
    )

    class Meta:
        model = PedidoCompra
        fields = [
            "data_entrega_prevista", "data_entrega_efetiva",
            "numero_nota_fiscal", "data_nota_fiscal", "tipo_nota_fiscal",
            "observacoes",
        ]
        widgets = {
            "data_entrega_prevista": forms.DateInput(attrs={"type": "date"}),
            "data_entrega_efetiva": forms.DateInput(attrs={"type": "date"}),
            "data_nota_fiscal": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned = super().clean()
        prevista = cleaned.get("data_entrega_prevista")
        efetiva = cleaned.get("data_entrega_efetiva")
        if prevista and efetiva and efetiva < prevista:
            # Apenas aviso lógico — não bloqueia (entrega pode adiantar)
            pass
        return cleaned


# ═════════════════════════════════════════════════════════════
# 5. ANEXOS 
# ═════════════════════════════════════════════════════════════
class AnexoPedidoForm(forms.Form):
    arquivos = MultipleFileField(
        label=_("Arquivos"),
        required=True,
    )
    observacao = forms.CharField(
        label=_("Observação"),
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Descrição opcional (aplicada a todos)",
        }),
    )

class AnexoSolicitacaoForm(forms.Form):
    arquivos = MultipleFileField(required=False, label="Anexos")
    descricao = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

# ═════════════════════════════════════════════════════════════
# 6. Material 
# ═════════════════════════════════════════════════════════════

class MaterialForm(forms.ModelForm):
    """
    Formulário de Material.

    O parâmetro `filial` é OPCIONAL e usado APENAS para:
      - validações de unicidade (descrição + marca dentro da filial);
      - geração automática de código por filial.

    ⚠️ A PERSISTÊNCIA da filial é responsabilidade do `FilialCreateMixin`
       (que injeta `form.instance.filial_id`). Este form NÃO atribui
       `self.instance.filial`, evitando dupla escrita conflitante.
    """

    class Meta:
        model = Material
        fields = [
            "descricao", "classificacao", "tipo", "marca",
            "unidade", "valor_unitario", "ncm", "grupo_tributario",
            "equipamento_epi", "ferramenta_ref", "ativo",
        ]
        widgets = {
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
            "classificacao": forms.Select(attrs={"class": "form-select"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "marca": forms.TextInput(attrs={"class": "form-control"}),
            "unidade": forms.Select(attrs={"class": "form-select"}),
            "valor_unitario": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "ncm": forms.Select(attrs={"class": "form-select"}),
            "grupo_tributario": forms.Select(attrs={"class": "form-select"}),
            "equipamento_epi": forms.Select(attrs={"class": "form-select"}),
            "ferramenta_ref": forms.Select(attrs={"class": "form-select"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        # Captura a filial ANTES de chamar super() (não é campo do form)
        self.filial = kwargs.pop("filial", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        descricao = (cleaned.get("descricao") or "").strip()
        marca = (cleaned.get("marca") or "").strip()

        # Validação de unicidade ESCOPADA por filial (descrição + marca)
        if descricao:
            qs = Material.objects.filter(
                descricao__iexact=descricao,
                marca__iexact=marca,
            )
            # Considera a filial ativa OU catálogo global
            if self.filial is not None:
                qs = qs.filter(filial=self.filial)

            # Exclui o próprio objeto em edição
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error(
                    "descricao",
                    "Já existe um material com esta descrição e marca nesta filial."
                )
        return cleaned
    

class VerbaContratoForm(forms.ModelForm):
    class Meta:
        model = VerbaContrato
        fields = [
            "contrato", "ano", "mes",
            "verba_epi", "verba_consumo", "verba_ferramenta",
        ]
        widgets = {
            "contrato": forms.Select(attrs={"class": "form-select"}),
            "ano": forms.NumberInput(attrs={
                "class": "form-control", "min": 2020, "max": 2100,
            }),
            "mes": forms.Select(attrs={"class": "form-select"}),
            "verba_epi": forms.NumberInput(attrs={
                "class": "form-control", "step": "0.01", "min": 0,
            }),
            "verba_consumo": forms.NumberInput(attrs={
                "class": "form-control", "step": "0.01", "min": 0,
            }),
            "verba_ferramenta": forms.NumberInput(attrs={
                "class": "form-control", "step": "0.01", "min": 0,
            }),
        }

    MESES = [
        (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"), (4, "Abril"),
        (5, "Maio"), (6, "Junho"), (7, "Julho"), (8, "Agosto"),
        (9, "Setembro"), (10, "Outubro"), (11, "Novembro"), (12, "Dezembro"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mes"].widget = forms.Select(
            choices=self.MESES, attrs={"class": "form-select"}
        )
        if not self.instance.pk:
            hoje = timezone.now()
            self.fields["ano"].initial = hoje.year
            self.fields["mes"].initial = hoje.month

    def clean(self):
        cleaned = super().clean()
        contrato = cleaned.get("contrato")
        ano = cleaned.get("ano")
        mes = cleaned.get("mes")

        if contrato and ano and mes:
            qs = VerbaContrato.objects.filter(
                contrato=contrato, ano=ano, mes=mes
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"Já existe verba cadastrada para {contrato.cm} "
                    f"em {mes:02d}/{ano}."
                )
        return cleaned
