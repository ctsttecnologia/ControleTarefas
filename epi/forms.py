from django import forms
from .models import FichaEPI, ItemEPI, EPI
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class FichaEPIForm(forms.ModelForm):
    class Meta:
        model = FichaEPI
        fields = ['cargo', 'registro', 'admissao', 'demissao', 'contrato', 'local_data', 'assinatura']
        widgets = {
            'admissao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'demissao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'registro': forms.TextInput(attrs={'class': 'form-control'}),
            'contrato': forms.TextInput(attrs={'class': 'form-control'}),
            'local_data': forms.TextInput(attrs={'class': 'form-control'}),
            'assinatura': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ItemEPIForm(forms.ModelForm):
    class Meta:
        model = ItemEPI
        fields = ['epi', 'quantidade', 'data_recebimento']
        widgets = {
            'epi': forms.Select(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'data_recebimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    def clean_quantidade(self):
        quantidade = self.cleaned_data.get('quantidade')
        if quantidade <= 0:
            raise forms.ValidationError("A quantidade deve ser maior que zero")
        return quantidade

class EPIForm(forms.ModelForm):
    class Meta:
        model = EPI
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'certificado': forms.TextInput(attrs={'class': 'form-control'}),
            'unidade': forms.TextInput(attrs={'class': 'form-control'}),
        }



