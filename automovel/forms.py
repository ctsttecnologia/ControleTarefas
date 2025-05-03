# automovel/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from datetime import datetime, timedelta

from .models import Carro, Agendamento, Checklist_Carro

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
            'cliente': forms.Select(attrs={'class': 'select2'}),
        }

    def clean(self):
        cleaned_data = super().clean()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        
        # Configurações de campos obrigatórios
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

# Checkilist do carro
class ChecklistCarroForm(forms.ModelForm):

    anexos_ocorrencia = forms.FileField(
        widget=forms.FileInput(attrs={
            
            'class': 'form-control-file'
        }),
        required=False,
        label='Anexos de Ocorrência'
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se estiver editando, não mostre o campo de múltiplos arquivos
        if self.instance and self.instance.pk:
            self.fields.pop('anexos_ocorrencia', None)

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            # Salve os arquivos múltiplos aqui se necessário
            # (veja a implementação na view abaixo)
        
        return instance

    class Meta:
        model = Checklist_Carro
        fields = '__all__'
        exclude = ['usuario', 'data_criacao', 'agendamento', 'tipo']
        widgets = {
            'observacoes_gerais': forms.Textarea(attrs={'rows': 4}),
            'foto_frontal': forms.FileInput(attrs={'accept': 'image/*', 'capture': 'environment'}),
            'observacoes_gerais': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Descreva qualquer problema ou ocorrência importante'
            }),
            
        }

    def clean(self):  # Manter apenas um método clean
        cleaned_data = super().clean()
        
        # Validação de coordenadas
        campos_coordenadas = [
            'coordenadas_avaria_frontal',
            'coordenadas_avaria_trazeira',
            'coordenadas_avaria_lado_motorista',
            'coordenadas_lado_passageiro'
        ]
        
        for campo in campos_coordenadas:
            valor = cleaned_data.get(campo)
            if valor:
                try:
                    x, y = map(float, valor.split(','))
                    if not (0 <= x <= 1000) or not (0 <= y <= 1000):
                        raise ValidationError(
                            f"{campo.replace('_', ' ').title()}: valores devem estar entre 0 e 1000"
                        )
                except ValueError:
                    raise ValidationError(
                        f"{campo.replace('_', ' ').title()}: use o formato 'x,y' com números"
                    )
        
        # Validação de quilometragem
        km_inicial = cleaned_data.get('km_inicial')
        km_final = cleaned_data.get('km_final')
        tipo = cleaned_data.get('tipo')
        
        if km_final is not None and km_inicial is not None:
            if km_final < km_inicial:
                self.add_error('km_final', 'O quilometragem final não pode ser menor que o inicial.')
        
        if tipo == 'retorno' and km_final is None:
            self.add_error('km_final', 'Quilometragem final é obrigatória para checklists de retorno.')
        
        return cleaned_data

class AssinaturaForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['assinatura']
        widgets = {
            'assinatura': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
                'capture': 'environment'  # Para dispositivos móveis
            })
        }

    # Atualize as mensagens de erro 
    error_messages = {
        'km_invalid': _('A quilometragem final não pode ser menor que a inicial.'),
        'km_required': _('Quilometragem final é obrigatória para checklists de retorno.'),
    }
    
    def clean(self):
        cleaned_data = super().clean()
        # ... código existente ...
        
        if km_final is not None and km_inicial is not None:
            if km_final < km_inicial:
                self.add_error('km_final', self.error_messages['km_invalid'])
        
        if tipo == 'retorno' and km_final is None:
            self.add_error('km_final', self.error_messages['km_required'])
        
        return cleaned_data

