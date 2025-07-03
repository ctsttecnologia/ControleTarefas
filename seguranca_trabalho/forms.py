
# seguranca_trabalho/forms.py (NOVO)

from django import forms
from .models import Equipamento, Funcao, FichaEPI, EntregaEPI


class EquipamentoForm(forms.ModelForm):
    class Meta:
        model = Equipamento
        fields = ['nome', 'certificado_aprovacao', 'vida_util_dias', 'estoque_minimo', 'ativo']
        
        # Widgets para aplicar as classes do Bootstrap e melhorar a interface
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Luva de Raspa'}),
            'certificado_aprovacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 12345'}),
            'vida_util_dias': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'estoque_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'vida_util_dias': 'Vida Útil em Dias',
            'estoque_minimo': 'Estoque Mínimo de Segurança',
        }

class FichaEPIForm(forms.ModelForm):
    class Meta:
        model = FichaEPI
        fields = ['colaborador', 'funcao', 'data_admissao']
        widgets = {'data_admissao': forms.DateInput(attrs={'type': 'date'})}

class EntregaEPIForm(forms.ModelForm):
    class Meta:
        model = EntregaEPI
        fields = ['equipamento', 'quantidade']

class AssinaturaForm(forms.Form):
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput())

