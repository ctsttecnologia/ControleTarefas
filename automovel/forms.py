# automovel/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Carro, Agendamento

class CarroForm(forms.ModelForm):
    class Meta:
        model = Carro
        fields = '__all__'
        widgets = {
            'data_ultima_manutencao': forms.DateInput(attrs={'type': 'date'}),
            'data_proxima_manutencao': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_placa(self):
        placa = self.cleaned_data['placa'].upper()
        return placa

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = '__all__'
        widgets = {
            'data_hora_agenda': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'data_hora_devolucao': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'ocorrencia': forms.Textarea(attrs={'rows': 3}),
            'motivo_cancelamento': forms.Textarea(attrs={'rows': 3}),
            'abastecimento': forms.CheckboxInput(),
        }


    def clean(self):
        cleaned_data = super().clean()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_hora_devolucao'].required = False
        self.fields['km_final'].required = False
        self.fields['foto_principal'].required = False
        self.fields['ocorrencia'].required = False
        self.fields['motivo_cancelamento'].required = False
        self.fields['descricao'].required = False

        

    def clean(self):
        cleaned_data = super().clean()
        cancelar_agenda = cleaned_data.get('cancelar_agenda')
        motivo_cancelamento = cleaned_data.get('motivo_cancelamento')
        status = cleaned_data.get('status')
        
        if (cancelar_agenda or status == 'cancelado') and not motivo_cancelamento:
            self.add_error('motivo_cancelamento', 'Este campo é obrigatório quando o agendamento é cancelado.')
        
        data_hora_agenda = cleaned_data.get('data_hora_agenda')
        data_hora_devolucao = cleaned_data.get('data_hora_devolucao')
        
        if data_hora_devolucao and data_hora_agenda and data_hora_devolucao <= data_hora_agenda:
            self.add_error('data_hora_devolucao', 'A data/hora de devolução deve ser posterior à data/hora de agendamento.')
        
        km_inicial = cleaned_data.get('km_inicial')
        km_final = cleaned_data.get('km_final')
        
        if km_final is not None and km_inicial is not None and km_final < km_inicial:
            self.add_error('km_final', 'A quilometragem final não pode ser menor que a inicial.')
        
        return cleaned_data
