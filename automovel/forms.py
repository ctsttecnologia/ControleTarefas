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
            'data_hora_agenda': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'data_hora_devolucao': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'descricao': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control'
            }),
            'ocorrencia': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control'
            }),
            'motivo_cancelamento': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control'
            }),
        }
        #labels = {
        #   'cm': 'Código do Contrato (CM)',
        #  'pedagio': 'Pedágio Necessário?',
        #    'abastecimento': 'Abastecimento Necessário?',
        #    'cancelar_agenda': 'Cancelar Agendamento?',
        #}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Definir campos como obrigatórios ou não
        self.fields['data_hora_devolucao'].required = False
        self.fields['km_final'].required = False
        self.fields['fotos'].required = False
        self.fields['assinatura'].required = True
        self.fields['ocorrencia'].required = False
        self.fields['motivo_cancelamento'].required = False
        self.fields['descricao'].required = False
        
        # Adicionar classes CSS para estilização
        for field in self.fields:
            if field not in ['pedagio', 'abastecimento', 'cancelar_agenda', 'status']:
                self.fields[field].widget.attrs.update({'class': 'form-control'})
            elif field in ['pedagio', 'abastecimento', 'cancelar_agenda']:
                self.fields[field].widget.attrs.update({'class': 'form-check-input'})

    def clean(self):
        cleaned_data = super().clean()
        cancelar_agenda = cleaned_data.get('cancelar_agenda')
        motivo_cancelamento = cleaned_data.get('motivo_cancelamento')
        status = cleaned_data.get('status')
        
        # Validação condicional para motivo de cancelamento
        if cancelar_agenda == 'S' and not motivo_cancelamento:
            self.add_error('motivo_cancelamento', 'Este campo é obrigatório quando o agendamento é cancelado.')
        
        # Validação para status cancelado
        if status == 'cancelado' and not motivo_cancelamento:
            self.add_error('motivo_cancelamento', 'Motivo do cancelamento é obrigatório para status "Cancelado".')
        
        # Validação de datas
        data_hora_agenda = cleaned_data.get('data_hora_agenda')
        data_hora_devolucao = cleaned_data.get('data_hora_devolucao')
        
        if data_hora_devolucao and data_hora_agenda and data_hora_devolucao <= data_hora_agenda:
            self.add_error('data_hora_devolucao', 'A data/hora de devolução deve ser posterior à data/hora de agendamento.')
        
        return cleaned_data