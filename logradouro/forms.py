from django import forms
from .models import Logradouro
from .constant import ESTADOS_BRASIL

class LogradouroForm(forms.ModelForm):
    class Meta:
        model = Logradouro
        fields = [
            'filial', 'endereco', 'numero', 'cep', 'complemento',
            'bairro', 'cidade', 'estado', 'pais',
            'ponto_referencia', 'latitude', 'longitude',
        ]
        
        widgets = {
            # O choices já é definido no modelo, não precisa ser redefinido aqui.
            'cep': forms.TextInput(attrs={
                'placeholder': 'Apenas números',
                'pattern': r'\d{8}',
                'title': 'Digite 8 dígitos numéricos.'
            }),
            'numero': forms.NumberInput(attrs={'min': 1}),
            'complemento': forms.TextInput(attrs={'placeholder': 'Ex: Apto 101, Bloco B'}),
            'latitude': forms.NumberInput(attrs={'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'step': '0.000001'}),
        }
        
        labels = {
            'endereco': 'Endereço (Rua, Av.)',
            'cep': 'CEP',
            'ponto_referencia': 'Ponto de Referência'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adiciona a classe do Bootstrap a todos os campos
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Opcional: Deixa o campo filial mais amigável, mostrando o nome da filial
        self.fields['filial'].label = "Filial do Endereço"
        self.fields['filial'].empty_label = "Selecione uma filial"

    def clean_cep(self):
        # A validação já é feita pelo RegexValidator no modelo, 
        # mas manter aqui é uma boa prática para feedback no formulário.
        cep = self.cleaned_data.get('cep')
        if cep and not cep.isdigit():
            raise forms.ValidationError("CEP deve conter apenas números.")
        if cep and len(cep) != 8:
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
        # Valida a extensão do arquivo
        if not file.name.endswith(('.csv', '.xlsx')):
            raise forms.ValidationError('Formato de arquivo não suportado. Use .csv ou .xlsx.')
        return file
    