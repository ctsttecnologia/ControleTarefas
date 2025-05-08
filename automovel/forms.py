from django import forms
from .models import Carro, Agendamento, Checklist, Foto
from django.contrib.auth.models import User

class CarroForm(forms.ModelForm):
    class Meta:
        model = Carro
        fields = '__all__'
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = '__all__'
        exclude = ['usuario', 'status', 'cancelar_agenda', 'data_hora_devolucao', 'km_final']
        widgets = {
            'data_hora_agenda': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'ocorrencia': forms.Textarea(attrs={'rows': 3}),
        }

class ChecklistForm(forms.ModelForm):
    class Meta:
        model = Checklist
        fields = '__all__'
        exclude = ['usuario', 'data_criacao', 'km_final', 'confirmacao']
        widgets = {
            'observacoes_gerais': forms.Textarea(attrs={'rows': 3}),
            'anexo_ocorrencia': forms.Textarea(attrs={'rows': 3}),
        }

class FotoForm(forms.ModelForm):
    class Meta:
        model = Foto
        fields = '__all__'
        exclude = ['data_criacao']

