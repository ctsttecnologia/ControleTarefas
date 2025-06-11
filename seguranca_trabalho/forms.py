from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import FichaEPI
from .models import EPIEquipamentoSeguranca

class FichaEPIForm(forms.ModelForm):
    class Meta:
        model = FichaEPI
        fields = '__all__'  # Inclui todos os campos do model
        # Personalizando os widgets (opcional)
        widgets = {
            'nome_colaborador': forms.TextInput(attrs={'placeholder': 'Nome do Colaborador'}),
            'equipamento': forms.TextInput(attrs={'placeholder': 'Nome do Equipamento'}),
            'ca_equipamento': forms.TextInput(attrs={'placeholder': 'Código CA do Equipamento'}),
            'data_entrega': forms.DateInput(attrs={'type': 'date'}),
            'data_devolucao': forms.DateInput(attrs={'type': 'date'}),
            'contrato_id': forms.NumberInput(attrs={'placeholder': 'ID do Contrato'}),
            'quantidade': forms.NumberInput(attrs={'placeholder': 'Quantidade'}),
            'descricao': forms.Textarea(attrs={'placeholder': 'Descrição', 'rows': 3}),
            'assinatura_colaborador': forms.HiddenInput(),  # Campo oculto para armazenar a assinatura       
        }

        # Personalizando os rótulos (opcional)
        labels = {
            'nome_colaborador': 'Nome do Colaborador',
            'equipamento': 'Equipamento',
            'ca_equipamento': 'Código CA do Equipamento',
            'data_entrega': 'Data de Entrega',
            'data_devolucao': 'Data de Devolução',
            'contrato_id': 'ID do Contrato',
            'quantidade': 'Quantidade',
            'descricao': 'Descrição',
        }

class EquipamentosSegurancaForm(forms.ModelForm):
    class Meta:
        model = EPIEquipamentoSeguranca
        fields = '__all__'
        widgets = {
            'nome_equipamento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Nome do equipamento')
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'codigo_ca': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'AA-1234'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 1,
                'placeholder': _('Descrição detalhada')
            }),
            'quantidade_estoque': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'estoque_minimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'data_validade': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'readonly': 'readonly'
            }),
            'ativo': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'nome_equipamento': _('Nome do Equipamento'),
            'tipo': _('Tipo'),
            'codigo_ca': _('Código CA'),
            'descricao': _('Descrição'),
            'quantidade_estoque': _('Quantidade em Estoque'),
            'estoque_minimo': _('Estoque Mínimo'),
            'data_validade': _('Data de Validade'),
            'ativo': _('Status'),
        }
        error_messages = {
            'nome_equipamento': {
                'required': _('O nome do equipamento é obrigatório'),
                'max_length': _('O nome não pode exceder 100 caracteres')
            },
            'codigo_ca': {
                'unique': _('Este código CA já está em uso'),
                'invalid': _('Formato inválido (use AA-1234)')
            }
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:  # Verifica se é uma edição
            self.fields['data_validade'].disabled = True
            self.fields['data_validade'].help_text = "A data de validade não pode ser alterada após o cadastro."
            # Garante que o valor original será usado mesmo se alguém manipular o HTML
            if self.instance.data_validade:
                self.initial['data_validade'] = self.instance.data_validade.strftime('%Y-%m-%d')   

    def clean(self):
        cleaned_data = super().clean()
        quantidade_estoque = cleaned_data.get('quantidade_estoque')
        estoque_minimo = cleaned_data.get('estoque_minimo')
        
        if quantidade_estoque is not None and estoque_minimo is not None:
            if quantidade_estoque < 0:
                self.add_error('quantidade_estoque', _('A quantidade não pode ser negativa'))
            if estoque_minimo < 1:
                self.add_error('estoque_minimo', _('O estoque mínimo deve ser pelo menos 1'))
            if quantidade_estoque < estoque_minimo:
                self.add_error(
                    None,
                    _('A quantidade em estoque está abaixo do mínimo definido')
                )
        
        return cleaned_data

class PesquisarFichaForm(forms.Form):
    nome_colaborador = forms.CharField(label='Nome do Colaborador', required=False)
    equipamento = forms.CharField(label='Equipamento', required=False)
    ca_equipamento = forms.CharField(label='Código CA', required=False)


