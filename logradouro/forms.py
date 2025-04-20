from django import forms
from .models import Logradouro
from .constants import ESTADOS_BRASIL

class LogradouroForm(forms.ModelForm):
    class Meta:
        model = Logradouro
        fields = [
            'endereco', 'numero', 'cep', 'complemento',
            'bairro', 'cidade', 'estado', 'pais',
            'ponto_referencia', 'latitude', 'longitude'
        ]
        
        widgets = {
            'estado': forms.Select(choices=ESTADOS_BRASIL),
            'cep': forms.TextInput(attrs={
                'placeholder': '00000000',
                'pattern': '\d{8}',
                'title': 'Digite 8 dígitos'
            }),
            'numero': forms.NumberInput(attrs={'min': 1}),
            'complemento': forms.TextInput(attrs={'placeholder': 'Opcional'}),
            'latitude': forms.NumberInput(attrs={'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'step': '0.000001'}),
        }
        
        labels = {
            'endereco': 'Endereço',
            'cep': 'CEP (apenas números)',
            'complemento': 'Complemento (opcional)',
            'ponto_referencia': 'Ponto de Referência (opcional)'
        }

    def clean_cep(self):
        cep = self.cleaned_data.get('cep')
        if len(cep) != 8:
            raise forms.ValidationError("CEP deve conter exatamente 8 dígitos")
        return cep
