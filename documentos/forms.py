# documentos/forms.py

from django import forms
from .models import Documento
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field


class DocumentoForm(forms.ModelForm):

    class Meta:
        model = Documento
        fields = ['nome', 'arquivo', 'data_emissao', 'data_vencimento']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Certificado NR-35',
            }),
            'data_emissao': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d',
            ),
            'data_vencimento': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d',
            ),
            'arquivo': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            Field('nome'),
            Field('arquivo'),
            Row(
                Column('data_emissao', css_class='col-md-6 mb-3'),
                Column('data_vencimento', css_class='col-md-6 mb-3'),
            ),
            Submit('submit', 'Salvar Documento', css_class='btn btn-success mt-2'),
        )

        
