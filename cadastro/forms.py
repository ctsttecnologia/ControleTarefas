from django import forms
from .models import Logradouro


class LogradouroForm(forms.ModelForm):
    class Meta:
        model = Logradouro
        fields = [  'endereco', 
                    'numero',
                    'cep',  
                    'complemento', 
                    'bairro', 
                    'cidade',
                    'estados', 
                    'pais'
                ]

