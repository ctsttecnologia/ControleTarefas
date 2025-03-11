from django import forms
from .models import Estados, Logradouro

class Estado(forms.ModelForm):
    class Meta:
        model = Estados
        fields = ['uf']

class Logradouro(forms.ModelForm):
    class Meta:
        model = Logradouro
        fields = ['estados', 
                    'endereco', 
                    'numero', 
                    'complemento', 
                    'bairro', 
                    'cidade', 
                    'cep', 
                    'pais'
                ]