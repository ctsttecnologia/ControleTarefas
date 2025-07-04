
# seguranca_trabalho/forms.py 

from django import forms
from .models import Equipamento, Funcao, FichaEPI, EntregaEPI, Fabricante, Fornecedor

# --- FORMULÁRIO DE FABRICANTE  ---
class FabricanteForm(forms.ModelForm):
    class Meta:
        model = Fabricante
        fields = ['nome', 'cnpj', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# --- FORMULÁRIO DE FORNECEDOR  ---
class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = ['razao_social', 'nome_fantasia', 'cnpj', 'email', 'telefone', 'ativo']
        widgets = {
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# --- FORMULÁRIO DE EQUIPAMENTO  ---
class EquipamentoForm(forms.ModelForm):
    class Meta:
        model = Equipamento
        fields = [
            'nome', 'modelo', 'fabricante', 'fornecedor_padrao', 
            'certificado_aprovacao', 'data_validade_ca', 'vida_util_dias',
            'estoque_minimo', 'requer_numero_serie', 'foto', 'observacoes', 'ativo'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Protetor Auricular Plug'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1100'}),
            'fabricante': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor_padrao': forms.Select(attrs={'class': 'form-select'}),
            'certificado_aprovacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 5745'}),
            'data_validade_ca': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'vida_util_dias': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'estoque_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'requer_numero_serie': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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



