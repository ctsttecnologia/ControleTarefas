# cliente/forms.py
from django import forms
from .models import Logradouro, Cliente
# Importe os modelos necessários

class ClienteForm(forms.ModelForm):
    logradouro = forms.ModelChoiceField(
        queryset=Logradouro.objects.all(),
        empty_label="Selecione um logradouro",
        widget=forms.Select(attrs={'required': True}),
    )

    # Personalizando o campo "unidade"
    unidade = forms.IntegerField(
        required=False,  # Torna o campo opcional
        widget=forms.NumberInput(attrs={'placeholder': 'Digite a unidade'}),
    )

    class Meta:
        model = Cliente
        fields = ['logradouro', 
                  'contrato', 
                  'razao_social', 
                  'unidade', 
                  'cnpj', 
                  'telefone', 
                  'data_de_inicio', 
                  'estatus']