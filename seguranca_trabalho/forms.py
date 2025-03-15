from django import forms

from .models import FichaEPI
from .models import EquipamentosSeguranca

class FichaEPIForm(forms.ModelForm):
    class Meta:
        model = FichaEPI
        fields = ['nome_colaborador', 
                  'equipamento', 
                  'ca_equipamento', 
                  'data_entrega', 
                  'data_devolucao',
                  'quantidade',
                  'descricao',
        ]


class EquipamentosSegurancaForm(forms.ModelForm):
    class Meta:
        model = EquipamentosSeguranca
        fields = [
            'nome_equioamento', 
            'tipo', 
            'codigo_ca', 
            'descricao', 
            'quantidade_estoque', 
            'data_validade', 
            'ativo'
        ]