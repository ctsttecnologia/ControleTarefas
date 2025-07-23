from django import forms
from .models import Logradouro
from .constant import ESTADOS_BRASIL

class LogradouroForm(forms.ModelForm):
    class Meta:
        model = Logradouro
        fields = [
            'endereco', 'numero', 'cep', 'complemento',
            'bairro', 'cidade', 'estado', 'pais',
            'ponto_referencia', 'latitude', 'longitude'
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

    def clean_cep(self):
        # A validação já é feita pelo RegexValidator no modelo, 
        # mas manter aqui é uma boa prática para feedback no formulário.
        cep = self.cleaned_data.get('cep')
        if cep and not cep.isdigit():
            raise forms.ValidationError("CEP deve conter apenas números.")
        if cep and len(cep) != 8:
            raise forms.ValidationError("CEP deve conter exatamente 8 dígitos.")
        return cep