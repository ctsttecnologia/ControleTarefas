from django import forms
from django.contrib.auth import get_user_model

from .models import Documento


class DocumentoAnexoForm(forms.ModelForm):
    """
    Formulário SIMPLES — usado quando se anexa documento a outro objeto
    (Funcionário, Treinamento, etc.) via GenericFK.
    """

    class Meta:
        model = Documento
        fields = ['nome', 'tipo', 'arquivo', 'data_emissao', 'data_vencimento']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Certificado NR-35',
            }),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d',
            ),
            'data_vencimento': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d',
            ),
            'arquivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class DocumentoEmpresaForm(forms.ModelForm):
    """
    Formulário COMPLETO — usado para documentos avulsos da empresa
    (contratos, alvarás, certidões, etc.) — substitui o antigo ArquivoForm.
    """
    class Meta:
        model = Documento
        fields = [
            'nome', 'tipo', 'cliente', 'descricao',
            'arquivo', 'data_emissao', 'data_vencimento',
            'dias_aviso', 'responsavel', 'status',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cliente': forms.Select(attrs={'class': 'form-select select2'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'arquivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'data_emissao': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d',
            ),
            'data_vencimento': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d',
            ),
            'dias_aviso': forms.NumberInput(attrs={'class': 'form-control'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtra responsáveis ativos
        self.fields['responsavel'].queryset = get_user_model().objects.filter(is_active=True)

        # Filtra clientes da filial do usuário
        if user and 'cliente' in self.fields:
            from cliente.models import Cliente
            self.fields['cliente'].queryset = Cliente.objects.filter(filial=user.filial_ativa)

        # Na edição, arquivo não é obrigatório (já tem um salvo)
        if self.instance and self.instance.pk:
            self.fields['arquivo'].required = False

    def save(self, commit=True, user=None):
        doc = super().save(commit=False)

        if user:
            if not doc.pk:
                doc.filial = user.filial_ativa
            if not doc.responsavel:
                doc.responsavel = user

        if commit:
            doc.save()

        return doc

        
