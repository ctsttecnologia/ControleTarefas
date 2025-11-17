
from django import forms
from .models import Documento
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

class DocumentoForm(forms.ModelForm):
    
    class Meta:
        model = Documento
        fields = ['nome', 'arquivo', 'data_emissao', 'data_vencimento']
        widgets = {
            'data_emissao': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d' # Garante o formato HTML5
            ),
            'data_vencimento': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configuração do Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'nome',
            'arquivo',
            Row(
                Column('data_emissao', css_class='form-group col-md-6 mb-0'),
                Column('data_vencimento', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', 'Salvar Documento', css_class='btn-success mt-3')
        )

        
