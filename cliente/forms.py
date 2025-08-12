from django import forms
from .models import Cliente
from django.utils import timezone

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'

        # A definição dos widgets já aplica as classes CSS necessárias.
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
        
        # Se a instância é nova (criando um cliente), define a data de início como hoje.
        if not self.instance.pk:
            self.fields['data_de_inicio'].initial = timezone.now().date()
        
        # Se a instância já existe (editando), desabilita os campos e garante a exibição dos valores.
        if self.instance and self.instance.pk:
            # Desabilita o campo e o torna não-obrigatório para a validação do formulário.
            self.fields['cnpj'].disabled = True
            self.fields['cnpj'].widget.attrs['title'] = 'O CNPJ não pode ser alterado.'
            
            self.fields['data_de_inicio'].disabled = True
            self.fields['data_de_inicio'].widget.attrs['title'] = 'A data de início não pode ser alterada.'
            
            # << CORREÇÃO DE EXIBIÇÃO >>
            # Força o widget a renderizar como <input type="text"> para que o valor apareça.
            self.fields['data_de_inicio'].widget.input_type = 'text'
            
            # Formata o valor para exibição no campo de texto no padrão brasileiro.
            if self.instance.data_de_inicio:
                self.initial['data_de_inicio'] = self.instance.data_de_inicio.strftime('%d/%m/%Y')

    def clean(self):
        """
        << CORREÇÃO FUNDAMENTAL >>
        Este método garante que os valores dos campos desabilitados não se percam ao salvar,
        evitando o erro "Este campo é obrigatório".
        """
        cleaned_data = super().clean()

        # Se estamos editando, restauramos os valores originais do banco de dados,
        # pois campos desabilitados não são enviados no formulário.
        if self.instance and self.instance.pk:
            cleaned_data['cnpj'] = self.instance.cnpj
            cleaned_data['data_de_inicio'] = self.instance.data_de_inicio
            
        return cleaned_data



