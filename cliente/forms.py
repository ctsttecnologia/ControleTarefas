# cliente/forms.py
from django import forms

from .models import Cliente

from logradouro.models import Logradouro

# Importe os modelos necessários

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        widgets = {
            'logradouro': forms.Select(attrs={
                'class': 'form-control select2',
                'style': 'width: 100%'
            }),
            'data_de_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['logradouro'].queryset = Logradouro.objects.all()
        self.fields['logradouro'].label_from_instance = lambda obj: f"{obj.endereco}, {obj.numero} - {obj.bairro}"

        