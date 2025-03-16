from django import forms
from .models import FichaEPI
from .models import EquipamentosSeguranca

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
        model = EquipamentosSeguranca
        fields = '__all__'  # Inclui todos os campos do model
           # Personalizando os widgets (opcional)
        widgets = {
            'nome_equioamento': forms.TextInput(attrs={'placeholder': 'Nome do equipamento'}),
            'tipo': forms.TextInput(attrs={'placeholder': 'Tipo (3 caracteres)'}),
            'codigo_ca': forms.TextInput(attrs={'placeholder': 'Código CA'}),
            'descricao': forms.Textarea(attrs={'placeholder': 'Descrição do equipamento', 'rows': 3}),
            'quantidade_estoque': forms.NumberInput(attrs={'placeholder': 'Quantidade em estoque'}),
            'data_validade': forms.DateInput(attrs={'type': 'date'}),
            'ativo': forms.Select(choices=[(1, 'Ativo'), (0, 'Inativo')]),
        }

        # Personalizando os rótulos (opcional)
        labels = {
            'nome_equioamento': 'Nome do Equipamento',
            'tipo': 'Tipo',
            'codigo_ca': 'Código CA',
            'descricao': 'Descrição',
            'quantidade_estoque': 'Quantidade em Estoque',
            'data_validade': 'Data de Validade',
            'ativo': 'Status',
        }

class PesquisarFichaForm(forms.Form):
    nome_colaborador = forms.CharField(label='Nome do Colaborador', required=False)
    equipamento = forms.CharField(label='Equipamento', required=False)
    ca_equipamento = forms.CharField(label='Código CA', required=False)
    