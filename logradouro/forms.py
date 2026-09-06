from django import forms
from .models import Logradouro
from .constant import ESTADOS_BRASIL
import re


class LogradouroForm(forms.ModelForm):
    # Sobrescreve o campo do model para permitir o hífen na digitação (00000-000)
    cep = forms.CharField(
        max_length=9,
        label='CEP',
        widget=forms.TextInput(attrs={
            'placeholder': '00000-000',
            'maxlength': '9',
            'inputmode': 'numeric',
            'title': 'Digite 8 dígitos numéricos.',
            'class': 'form-control cep-mask',
        })
    )

    class Meta:
        model = Logradouro
        fields = [
            'filial', 'endereco', 'numero', 'cep', 'complemento', 'tipo_logradouro',
            'bairro', 'cidade', 'estado', 'pais',
            'ponto_referencia', 'latitude', 'longitude',
        ]

        widgets = {
            'numero': forms.NumberInput(attrs={'min': 1}),
            'complemento': forms.TextInput(attrs={'placeholder': 'Ex: Apto 101, Bloco B'}),
            'latitude': forms.NumberInput(attrs={'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'step': '0.000001'}),
        }

        labels = {
            'endereco': 'Endereço (Rua, Av.)',
            'ponto_referencia': 'Ponto de Referência',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adiciona a classe do Bootstrap a todos os campos (sem sobrescrever classes já definidas)
        for field_name, field in self.fields.items():
            existing_classes = field.widget.attrs.get('class', '')
            if 'form-control' not in existing_classes:
                field.widget.attrs['class'] = f'{existing_classes} form-control'.strip()

        # Deixa o campo filial mais amigável, mostrando o nome da filial
        self.fields['filial'].label = "Filial do Endereço"
        self.fields['filial'].empty_label = "Selecione uma filial"

    def clean_cep(self):
        cep = self.cleaned_data.get('cep')
        if cep:
            cep = re.sub(r'\D', '', cep)  # remove tudo que não for dígito (ex: hífen)
            if len(cep) != 8:
                raise forms.ValidationError("CEP deve conter exatamente 8 dígitos.")
        return cep


# Upload para planilha de inserção de dados em massa

class UploadFileForm(forms.Form):
    file = forms.FileField(
        label='Selecione a planilha (.xlsx ou .csv)',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        help_text='O arquivo deve seguir o modelo padrão com as colunas: filial_id, endereco, numero, etc.'
    )

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.endswith(('.csv', '.xlsx')):
            raise forms.ValidationError('Formato de arquivo não suportado. Use .csv ou .xlsx.')
        return file

    