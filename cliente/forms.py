from django import forms
from .models import Cliente
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import zipfile

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_DESCOMPACTADO_BYTES = 50 * 1024 * 1024

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'razao_social',
            'nome',
            'cnpj',
            'contrato',
            'unidade',
            'inscricao_estadual',
            'inscricao_municipal',
            'telefone',
            'email',
            'logradouro',
            'data_de_inicio',
            'data_encerramento',
            'estatus',
            'observacoes',
        ]

        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'contrato': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0000'}),
            'unidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'logradouro': forms.Select(attrs={'class': 'form-select'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'inscricao_municipal': forms.TextInput(attrs={'class': 'form-control'}),
            'data_de_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_encerramento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estatus': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['data_de_inicio'].initial = timezone.now().date()

        if self.instance and self.instance.pk:
            self.fields["cnpj"].widget.attrs.pop("readonly", None)
            self.fields["cnpj"].widget.attrs.pop("disabled", None)
            self.fields["cnpj"].disabled = False

            self.fields['data_de_inicio'].disabled = True
            self.fields['data_de_inicio'].widget.attrs['title'] = 'A data de início não pode ser alterada.'

            self.fields['data_de_inicio'].widget.input_type = 'text'

            if self.instance.data_de_inicio:
                self.initial['data_de_inicio'] = self.instance.data_de_inicio.strftime('%d/%m/%Y')

    def clean(self):
        cleaned_data = super().clean()

        if self.instance and self.instance.pk:
            cleaned_data['cnpj'] = self.instance.cnpj
            cleaned_data['data_de_inicio'] = self.instance.data_de_inicio

        return cleaned_data


class ImportacaoMassaForm(forms.Form):
    """Form para upload de planilha de importação em massa."""

    arquivo = forms.FileField(
        label=_("Planilha Excel (.xlsx)"),
        help_text=_("Envie o arquivo .xlsx preenchido com base no modelo."),
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx", "class": "form-control"}),
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get("arquivo")
        if not arquivo:
            return arquivo

        if not arquivo.name.lower().endswith(".xlsx"):
            raise forms.ValidationError(_("Apenas arquivos .xlsx são aceitos."))

        if arquivo.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError(_("Arquivo muito grande. Tamanho máximo: 5MB."))

        # Assinatura ZIP (xlsx é um zip)
        cabecalho = arquivo.read(4)
        arquivo.seek(0)
        if cabecalho != b"PK\x03\x04":
            raise forms.ValidationError(_("O arquivo não é um .xlsx válido."))

        # Proteção contra zip bomb + estrutura mínima de xlsx
        try:
            with zipfile.ZipFile(arquivo) as zf:
                nomes = zf.namelist()
                if "xl/workbook.xml" not in nomes:
                    raise forms.ValidationError(_("O arquivo não é um .xlsx válido."))
                if sum(i.file_size for i in zf.infolist()) > MAX_DESCOMPACTADO_BYTES:
                    raise forms.ValidationError(_("Arquivo excede o tamanho permitido."))
        except zipfile.BadZipFile:
            raise forms.ValidationError(_("O arquivo está corrompido ou não é um .xlsx."))
        finally:
            arquivo.seek(0)

        return arquivo

