# ferramentas/forms.py
from django import forms
from .models import Ferramenta, Movimentacao

class FerramentaForm(forms.ModelForm):
    class Meta:
        model = Ferramenta
        # ADICIONADO O CAMPO 'patrimonio'
        fields = ['nome', 'patrimonio', 'codigo_identificacao', 'fabricante', 'localizacao_padrao', 'data_aquisicao', 'status', 'observacoes']
        
        # WIDGETS ADICIONADOS PARA TODOS OS CAMPOS COM CLASSES BOOTSTRAP
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Furadeira de Impacto'
            }),
            'patrimonio': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nº de patrimônio ou ativo fixo'
            }),
            'codigo_identificacao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código único, ex: FR-001'
            }),
            'fabricante': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Bosch, DeWalt'
            }),
            'localizacao_padrao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Armário 2, Prateleira A'
            }),
            'data_aquisicao': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Informações adicionais, histórico de manutenção, etc.'
            }),
        }

class RetiradaForm(forms.ModelForm):
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput(), required=True)

    class Meta:
        model = Movimentacao
        # ATUALIZADO de 'usuario_retirada' para 'retirado_por'
        fields = ['retirado_por', 'data_devolucao_prevista', 'condicoes_retirada']
        
        # WIDGETS ADICIONADOS COM CLASSES BOOTSTRAP
        widgets = {
            'retirado_por': forms.Select(attrs={
                'class': 'form-select'
            }),
            'data_devolucao_prevista': forms.DateTimeInput(attrs={
                'type': 'datetime-local', 
                'class': 'form-control'
            }),
            'condicoes_retirada': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Descreva as condições da ferramenta no momento da retirada.'
            }),
        }

class DevolucaoForm(forms.ModelForm):
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput(), required=True)
    
    class Meta:
        model = Movimentacao
        fields = ['condicoes_devolucao']
        
        # WIDGET ATUALIZADO COM CLASSE BOOTSTRAP
        widgets = {
            'condicoes_devolucao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3, 
                'placeholder': 'Descreva como a ferramenta foi devolvida. Aponte qualquer dano ou problema.'
            }),
        }