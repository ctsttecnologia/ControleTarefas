  
from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'  # Garante que todos os campos, incluindo 'contrato', sejam incluídos

        # Define classes e atributos diretamente aqui, sem loops complexos
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

    # O método __init__ não é mais necessário para adicionar classes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Loop para aplicar classes CSS do Bootstrap
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

        # Se a instância já existe (estamos editando), torna os campos readonly
        if self.instance and self.instance.pk:
            self.fields['cnpj'].widget.attrs['readonly'] = True
            self.fields['cnpj'].widget.attrs['title'] = 'O CNPJ não pode ser alterado.'
            
            self.fields['data_de_inicio'].widget.attrs['readonly'] = True
            self.fields['data_de_inicio'].widget.attrs['title'] = 'A data de início não pode ser alterada.'
    