from django import forms
from .models import Cliente
from django.utils import timezone

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'razao_social',
            'nome',
            'cnpj',
            'contrato',
            'unidade',
            'inscricao_estadual',
            'inscricao_municipal',
            'telefone',
            'email',
            'logradouro',
            'data_de_inicio',
            'data_encerramento',
            'estatus',
            'observacoes',
        ]

        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'contrato': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0000'}),
            'unidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'logradouro': forms.Select(attrs={'class': 'form-select'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'inscricao_municipal': forms.TextInput(attrs={'class': 'form-control'}),
            'data_de_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_encerramento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estatus': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['data_de_inicio'].initial = timezone.now().date()

        if self.instance and self.instance.pk:
            self.fields['cnpj'].disabled = True
            self.fields['cnpj'].widget.attrs['title'] = 'O CNPJ não pode ser alterado.'

            self.fields['data_de_inicio'].disabled = True
            self.fields['data_de_inicio'].widget.attrs['title'] = 'A data de início não pode ser alterada.'

            self.fields['data_de_inicio'].widget.input_type = 'text'

            if self.instance.data_de_inicio:
                self.initial['data_de_inicio'] = self.instance.data_de_inicio.strftime('%d/%m/%Y')

    def clean(self):
        cleaned_data = super().clean()

        if self.instance and self.instance.pk:
            cleaned_data['cnpj'] = self.instance.cnpj
            cleaned_data['data_de_inicio'] = self.instance.data_de_inicio

        return cleaned_data

