from django import forms
from .models import Logradouro
from .constant import ESTADOS_BRASIL  # Importe sua lista de estados

class LogradouroForm(forms.ModelForm):
    class Meta:
        model = Logradouro
        fields = [  
            'endereco', 
            'numero',
            'cep',  
            'complemento', 
            'bairro', 
            'cidade',
            'estado',
            'pais'
        ]
        
        # CORREÇÃO: widgets deve ser um dicionário, não uma lista
        widgets = {
            'estado': forms.Select(choices=ESTADOS_BRASIL),
            'cep': forms.TextInput(attrs={'placeholder': '00000-000'}),
            'numero': forms.NumberInput(attrs={'min': 1}),
            'complemento': forms.TextInput(attrs={'placeholder': 'Opcional'}),
        }
        
        # Opcional: labels personalizados
        labels = {
            'endereco': 'Endereço',
            'cep': 'CEP',
            'complemento': 'Complemento (opcional)'
        }

    # Validação customizada do CEP (opcional)
    def clean_cep(self):
        cep = self.cleaned_data.get('cep')
        # Adicione sua lógica de validação aqui
        if len(cep) < 8:
            raise forms.ValidationError("CEP inválido")
        return cep