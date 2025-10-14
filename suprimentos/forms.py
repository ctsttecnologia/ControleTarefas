
# suprimentos/forms.py
from django import forms
from .models import Parceiro
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ParceiroForm(forms.ModelForm):
    class Meta:
        model = Parceiro
        fields = [
            'nome_fantasia', 'razao_social', 'cnpj', 'inscricao_estadual',
            'endereco', 'email', 'telefone', 'celular', 'contato', 'site',
            'observacoes', 'eh_fabricante', 'eh_fornecedor', 'ativo', 'filial'
        ]
        widgets = {
            'filial': forms.Select(attrs={'class': 'form-select'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Fantasia ou Nome do Fabricante'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 0000-0000'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'contato': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pessoa de contato'}),
            'site': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.exemplo.com'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'eh_fabricante': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'eh_fornecedor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
class UploadFileForm(forms.Form):
    file = forms.FileField(
        label=_("Selecione a planilha (.xlsx)"),
        help_text=_("Apenas arquivos no formato .xlsx são aceitos."),
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.endswith('.xlsx'):
                raise ValidationError(_("Arquivo inválido. Por favor, envie uma planilha no formato .xlsx."))
        return file