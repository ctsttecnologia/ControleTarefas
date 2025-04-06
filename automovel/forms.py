from django import forms
from .models import Carro, Agendamento
from django.core.exceptions import ValidationError
from datetime import datetime

class CarroForm(forms.ModelForm):
    class Meta:
        model = Carro
        fields = '__all__'
        widgets = {
            'data_ultima_manutencao': forms.DateInput(attrs={'type': 'date'}),
            'data_proxima_manutencao': forms.DateInput(attrs={'type': 'date'}),
        }

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = '__all__'
        widgets = {
            'data_hora_agenda': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'data_hora_devolucao': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'assinatura': forms.HiddenInput(),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        data_agenda = cleaned_data.get('data_hora_agenda')
        data_devolucao = cleaned_data.get('data_hora_devolucao')
        
        if data_agenda and data_devolucao and data_agenda >= data_devolucao:
            raise ValidationError("A data de devolução deve ser posterior à data de agendamento.")
        
        return cleaned_data