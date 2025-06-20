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
                'style': 'width: 100%'
            }),
            'data_de_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'readonly': True  # Torna o campo readonly no HTML
            }),
            'cnpj': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True  # Torna o campo readonly no HTML
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
            'cep': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000-000'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'estatus': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'nome': 'Nome/Razão Social',
            'cnpj': 'CNPJ (não editável)',
            'data_de_inicio': 'Data de Início (não editável)'
        }
        help_texts = {
            'cnpj': 'Este campo não pode ser alterado após o cadastro',
            'data_de_inicio': 'Data fixa que não pode ser modificada'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configuração do queryset para logradouro
        self.fields['logradouro'].queryset = Logradouro.objects.all()
        self.fields['logradouro'].label_from_instance = lambda obj: f"{obj.endereco}, {obj.numero} - {obj.bairro}"
        
        if self.instance and self.instance.pk:
            # Desabilita campos que não podem ser editados
            self.fields['cnpj'].disabled = True
            self.fields['data_de_inicio'].disabled = True
        
    
    def clean_cnpj(self):
        """Validação adicional para CNPJ (se necessário)"""
        cnpj = self.cleaned_data.get('cnpj')
        if self.instance and self.instance.pk:
            # Garante que o CNPJ não seja alterado na edição
            if cnpj != self.instance.cnpj:
                raise forms.ValidationError("Não é permitido alterar o CNPJ de um cliente existente.")
        return cnpj
    
    def clean_data_de_inicio(self):
        """Validação adicional para data de início"""
        data_de_inicio = self.cleaned_data.get('data_de_inicio')
        if self.instance and self.instance.pk:
            # Garante que a data de início não seja alterada na edição
            if data_de_inicio != self.instance.data_de_inicio:
                raise forms.ValidationError("Não é permitido alterar a data de início de um contrato existente.")
        return data_de_inicio