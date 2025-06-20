
from datetime import timedelta
import os
from django import forms
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import DurationField

from tarefas.admin import ComentarioAdmin, Comentario
from .models import Tarefas, User


class TarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefas
        fields = [
            'titulo', 'descricao', 'status', 'prioridade',
            'data_inicio', 'prazo', 'responsavel', 'projeto',
            'duracao_prevista', 'tempo_gasto', 'dias_lembrete', 'data_lembrete'
        ]
        
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'prioridade': forms.Select(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'prazo': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'responsavel': forms.Select(attrs={'class': 'form-control'}),
            'projeto': forms.TextInput(attrs={'class': 'form-control'}),
            'duracao_prevista': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'DD HH:MM:SS'
            }),
            'tempo_gasto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'DD HH:MM:SS'
            }),
            'dias_lembrete': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 30
            }),
            'data_lembrete': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
        }
        
        help_texts = {
            'duracao_prevista': 'Formato: dias HH:MM:SS (ex: 1 02:30:00 para 1 dia e 2 horas e 30 minutos)',
            'tempo_gasto': 'Formato: dias HH:MM:SS',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            self.fields['data_inicio'].disabled = True
            self.fields['data_inicio'].help_text = 'Data de início não pode ser alterada após criação'
        
        # Filtra responsáveis da mesma equipe se houver
        if self.request and hasattr(self.request.user, 'equipe'):
            self.fields['responsavel'].queryset = User.objects.filter(
                equipe=self.request.user.equipe
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk and self.request and self.request.user.is_authenticated:
            instance.usuario = self.request.user
        if commit:
            instance.save()
        return instance
    def clean_duracao_prevista(self):
        data = self.cleaned_data.get('duracao_prevista')
        if data and data > timedelta(days=30):
            raise forms.ValidationError("A duração não pode exceder 30 dias")
        return data
    
    def clean_tempo_gasto(self):
        data = self.cleaned_data.get('tempo_gasto')
        if data and data > timedelta(days=30):
            raise forms.ValidationError("O tempo gasto não pode exceder 30 dias")
        return data
    
class DurationInput(forms.TextInput):
    input_type = 'text'

class TarefaForm(forms.ModelForm):
    tempo_gasto = DurationField(
        widget=DurationInput(attrs={'placeholder': 'DD HH:MM:SS'}),
        required=False,
        validators=[
            MaxValueValidator(
                timedelta(days=1),
                message="O tempo não pode exceder 24 horas"
            )
        ]
    )

    class Meta:
        model = Tarefas
        fields = '__all__'

    def clean_tempo_gasto(self):
        data = self.cleaned_data.get('tempo_gasto')
        if data and data.total_seconds() > 86400:  # 24h em segundos
            raise forms.ValidationError("Duração máxima permitida é de 24 horas")
        return data

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto', 'anexo']
        widgets = {
            'texto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'anexo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif'
            })
        }

    def clean_anexo(self):
        anexo = self.cleaned_data.get('anexo')
        if anexo:
            if anexo.size > ComentarioAdmin.TAMANHO_MAXIMO_ANEXO:
                raise forms.ValidationError(
                    f'Tamanho máximo permitido: {Comentario.TAMANHO_MAXIMO_ANEXO // (1024*1024)}MB'
                )
            ext = os.path.splitext(anexo.name)[1][1:].lower()
            if ext not in Comentario.EXTENSOES_PERMITIDAS: # type: ignore
                raise forms.ValidationError(
                    f'Extensões permitidas: {", ".join(Comentario.EXTENSOES_PERMITIDAS)}'
                )
        return anexo

