# seguranca_trabalho/forms.py


from django import forms
from django.utils.translation import gettext_lazy as _
import pathlib
from .models import Equipamento, FichaEPI, EntregaEPI, Funcao, CargoFuncao
from departamento_pessoal.models import Funcionario
from suprimentos.models import Parceiro
from django_select2.forms import ModelSelect2Widget
from django.core.exceptions import ValidationError

import base64
import binascii


from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

try:
    from PIL import Image
except ImportError:
    Image = None

from .models import EntregaEPI, FichaEPI

# Limite de tamanho para a assinatura (base64 ou upload), em bytes
MAX_ASSINATURA_BYTES = 500_000  # ~500KB
FORMATOS_IMAGEM_VALIDOS = ("PNG", "JPEG")

class EquipamentoForm(forms.ModelForm):
    estoque_inicial = forms.IntegerField(
        required=False,
        min_value=0,
        label=_("Estoque Atual"),
        help_text=_("Quantidade inicial em estoque. Será registrada como entrada de inventário."),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': '0'}),
    )

    class Meta:
        model = Equipamento
        fields = [
            'nome', 'modelo', 'fabricante',
            'certificado_aprovacao', 'data_validade_ca', 'vida_util_dias',
            'estoque_minimo', 'requer_numero_serie', 'foto', 'observacoes', 'ativo',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Protetor Auricular Plug'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1100'}),
            'fabricante': ModelSelect2Widget(
                model=Parceiro,
                search_fields=['nome_fantasia__icontains', 'razao_social__icontains'],
                attrs={
                    'class': 'form-control',
                    'data-placeholder': 'Buscar fabricante...'
                }
            ),
            'certificado_aprovacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 5745'}),
            'data_validade_ca': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'vida_util_dias': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'estoque_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'requer_numero_serie': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fabricante'].queryset = Parceiro.objects.filter(eh_fabricante=True)

        if self.instance.pk:
            # Edição: campos CA readonly
            self.fields['certificado_aprovacao'].widget.attrs['readonly'] = True
            self.fields['data_validade_ca'].widget = forms.TextInput(
                attrs={'class': 'form-control-plaintext', 'readonly': True}
            )
            if self.instance.data_validade_ca:
                self.initial['data_validade_ca'] = self.instance.data_validade_ca.strftime('%d/%m/%Y')

            # Estoque: readonly na edição, mostra valor atual
            self.fields['estoque_inicial'].label = _("Estoque Atual")
            self.fields['estoque_inicial'].initial = self.instance.estoque_atual
            self.fields['estoque_inicial'].help_text = _(
                "Atualizado automaticamente. Use 'Ajuste de Estoque' para alterar."
            )
            self.fields['estoque_inicial'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control bg-light fw-bold',
                'tabindex': '-1',
            })
        else:
            # Criação: campo editável
            self.fields['estoque_inicial'].label = _("Estoque Inicial")
            self.fields['estoque_inicial'].help_text = _(
                "Quantidade em estoque. Será registrada como entrada de inventário."
            )


class FichaEPIForm(forms.ModelForm):
    class Meta:
        model = FichaEPI
        fields = ['funcionario']
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request:
            filial_id = request.session.get('active_filial_id')
            qs = Funcionario.objects.filter(status='ATIVO')

            if filial_id:
                qs = qs.filter(filial_id=filial_id)

            # ── Regra de negócio: não permitir selecionar funcionário
            #    que já possui ficha de EPI ativa ──
            qs = qs.exclude(ficha_epi__isnull=False)

            self.fields['funcionario'].queryset = qs.order_by('nome_completo')

    def clean_funcionario(self):
        funcionario = self.cleaned_data.get('funcionario')
        if funcionario and (not hasattr(funcionario, 'cargo') or not funcionario.cargo):
            raise forms.ValidationError(
                _("O funcionário selecionado não possui um cargo definido. "
                  "Por favor, atualize o cadastro no Departamento Pessoal."),
                code='sem_cargo'
            )
        return funcionario


class EntregaEPIForm(forms.ModelForm):
    class Meta:
        model = EntregaEPI
        fields = ['equipamento', 'quantidade', 'lote', 'numero_serie']
        widgets = {
            'equipamento': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'lote': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        filial = kwargs.pop('filial', None)
        super().__init__(*args, **kwargs)

        # Filtra equipamentos pela filial (lógica mantida)
        queryset = Equipamento.objects.filter(ativo=True)
        if filial:
            queryset = queryset.filter(filial=filial)
        self.fields['equipamento'].queryset = queryset

class AssinaturaForm(forms.Form):
    """Formulário simples para capturar a assinatura em base64 do frontend."""
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput())
    consentimento_lgpd = forms.BooleanField(
        required=True,
        error_messages={
            "required": _("É necessário consentir com o tratamento da sua assinatura.")
        },
    )

    def clean_assinatura_base64(self):
        valor = (self.cleaned_data.get("assinatura_base64") or "").strip()
        if not valor:
            raise ValidationError(_("A assinatura não pode estar vazia."))
        _validar_base64_assinatura(valor)
        return valor


class AssinaturaMixinLGPD(forms.ModelForm):
    """
    Mixin comum para forms de assinatura: valida o payload vindo do
    signature_pad (base64) e/ou upload de imagem, exige consentimento
    explícito (LGPD, Art. 7º, II — cumprimento de obrigação legal/NR-06)
    e limita o tamanho do dado armazenado.
    """
    consentimento_lgpd = forms.BooleanField(
        required=True,
        error_messages={
            "required": _("É necessário consentir com o tratamento da sua assinatura.")
        },
    )

    def clean(self):
        cleaned = super().clean()
        sig_b64 = (self.data.get("assinatura_base64") or "").strip()

        if sig_b64:
            _validar_base64_assinatura(sig_b64)

        arquivo = self.files.get(self._upload_field_name) if hasattr(self, "_upload_field_name") else None
        if arquivo:
            _validar_upload_imagem(arquivo)

        if not sig_b64 and not arquivo:
            raise ValidationError(_("É necessário desenhar ou enviar uma assinatura."))


        return cleaned


class AssinaturaEntregaForm(AssinaturaMixinLGPD):
    """Formulário para assinatura de entrega: aceita canvas (base64) OU upload de imagem."""

    _upload_field_name = "assinatura_imagem"
    assinatura_imagem = forms.ImageField(required=False)
    assinatura_base64 = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = EntregaEPI
        fields = []  # nada é salvo direto via ModelForm — a view chama entrega.salvar_assinatura()

    
class AssinaturaTermoForm(AssinaturaMixinLGPD):
    """Formulário para assinatura de termo (Ficha EPI)."""

    _upload_field_name = "assinatura_imagem"
    assinatura_imagem = forms.ImageField(required=False)

    class Meta:
        model = FichaEPI
        fields = ["assinatura_funcionario"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assinatura_funcionario"].widget = forms.HiddenInput()
        self.fields["assinatura_funcionario"].required = False


# ── Helpers de validação compartilhados ──────────────────────────────────

def _validar_base64_assinatura(valor: str) -> None:
    """Valida tamanho e integridade do payload base64 do signature_pad."""
    if len(valor) > MAX_ASSINATURA_BYTES:
        raise ValidationError(_("Assinatura excede o tamanho permitido."))

    # Formato esperado: "data:image/png;base64,XXXXX"
    if "," in valor:
        header, payload = valor.split(",", 1)
        if "image/png" not in header and "image/jpeg" not in header:
            raise ValidationError(_("Formato de assinatura não suportado."))
    else:
        payload = valor

    try:
        decoded = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise ValidationError(_("Assinatura corrompida ou em formato inválido."))

    if Image is not None:
        try:
            from io import BytesIO
            img = Image.open(BytesIO(decoded))
            img.verify()
            if img.format not in FORMATOS_IMAGEM_VALIDOS:
                raise ValidationError(_("Formato de imagem não suportado."))
        except ValidationError:
            raise
        except Exception:
            raise ValidationError(_("Assinatura não é uma imagem válida."))


def _validar_upload_imagem(arquivo) -> None:
    """Valida tamanho, mimetype declarado e conteúdo real do upload."""
    if arquivo.size > MAX_ASSINATURA_BYTES:
        raise ValidationError(
            _("Arquivo maior que %(mb).1fMB.") % {"mb": MAX_ASSINATURA_BYTES / (1024 * 1024)}
        )

    if arquivo.content_type not in ("image/png", "image/jpeg"):
        raise ValidationError(_("Formato inválido. Envie apenas PNG ou JPEG."))

    if Image is None:
        return  # Pillow não instalado — validação de conteúdo fica só client-side

    try:
        img = Image.open(arquivo)
        img.verify()
        if img.format not in FORMATOS_IMAGEM_VALIDOS:
            raise ValidationError(_("Formato de imagem não suportado."))
    except ValidationError:
        raise
    except Exception:
        raise ValidationError(_("Arquivo de imagem inválido ou corrompido."))
    finally:
        arquivo.seek(0)  # reposiciona o ponteiro após a verificação


class FuncaoForm(forms.ModelForm):
    class Meta:
        model = Funcao
        # Vamos incluir apenas os campos que o usuário deve preencher.
        # A 'filial' será adicionada automaticamente na view.
        fields = ['nome', 'ativo', 'descricao', 'registro']
        widgets = {
            'registro': forms.NumberInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

        }

class CargoFuncaoForm(forms.ModelForm):
    class Meta:
        model = CargoFuncao
        fields = ['cargo', 'funcao']

    def clean(self):
        cleaned_data = super().clean()
        cargo = cleaned_data.get('cargo')
        funcao = cleaned_data.get('funcao')

        if cargo and funcao:
            # Exclui o próprio objeto em caso de edição
            qs = CargoFuncao.objects.filter(cargo=cargo, funcao=funcao)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"A associação entre '{cargo}' e '{funcao}' já existe."
                )

        return cleaned_data

class AjusteEstoqueForm(forms.Form):
    TIPO_CHOICES = [
        ('ENTRADA', _('Entrada (adicionar ao estoque)')),
        ('SAIDA', _('Saída (remover do estoque)')),
    ]

    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        label=_("Tipo de Ajuste"),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    quantidade = forms.IntegerField(
        min_value=1,
        label=_("Quantidade"),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Ex: 10'}),
    )
    justificativa = forms.CharField(
        label=_("Justificativa"),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: Compra NF 12345 / Ajuste de inventário'}),
    )
