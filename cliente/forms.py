  

from django import forms
from .models import Cliente
from logradouro.models import Logradouro


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        widgets = {
            'logradouro': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Selecione um endereço...',
                'style': 'width: 100%'
            }),
            'data_de_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'readonly': True
            }),
            'cnpj': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'estatus': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'inscricao_estadual': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'inscricao_municipal': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'nome': 'Nome/Razão Social',
            'cnpj': 'CNPJ (não editável)',
            'data_de_inicio': 'Data de Início (não editável)',
        }
        help_texts = {
            'cnpj': 'Este campo não pode ser alterado após o cadastro',
            'data_de_inicio': 'Data fixa que não pode ser modificada'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ajuste visual do dropdown de logradouros
        self.fields['logradouro'].queryset = Logradouro.objects.all()
        self.fields['logradouro'].label_from_instance = lambda obj: (
            f"{obj.endereco}, {obj.numero} - {obj.bairro}"
        )

        if self.instance and self.instance.pk:
            # Desabilita campos não editáveis
            for field_name in ['cnpj', 'data_de_inicio']:
                self.fields[field_name].disabled = True

    def clean_cnpj(self):
        """Garante que o CNPJ não seja alterado em edições"""
        cnpj = self.cleaned_data.get('cnpj', self.instance.cnpj)
        if self.instance.pk and cnpj != self.instance.cnpj:
            raise forms.ValidationError("Não é permitido alterar o CNPJ de um cliente já cadastrado.")
        return cnpj

    def clean_data_de_inicio(self):
        """Garante que a data de início não seja alterada em edições"""
        data = self.cleaned_data.get('data_de_inicio')
        if self.instance.pk and data != self.instance.data_de_inicio:
            raise forms.ValidationError("Não é permitido alterar a data de início.")
        return data
    

    