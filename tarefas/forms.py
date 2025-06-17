from django import forms
from .models import Tarefas, Comentario
from django.contrib.auth import get_user_model


User = get_user_model()

class TarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefas
        fields = '__all__'
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': ('Título da tarefa')
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': ('Descrição detalhada...')
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'prioridade': forms.Select(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'prazo': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'concluida_em': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'disabled': True
            }, format='%Y-%m-%dT%H:%M'),
            'data_lembrete': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'usuario': forms.Select(attrs={
                'class': 'form-control',
                'disabled': True
            }),
            'responsavel': forms.Select(attrs={'class': 'form-control'}),
            'projeto': forms.TextInput(attrs={'class': 'form-control'}),
            'duracao_prevista': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'tempo_gasto': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'dias_lembrete': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 30
            }),
        }
        help_texts = {
            'dias_lembrete': ('Dias antes do prazo para enviar lembrete'),
            'data_lembrete': ('Data específica para envio de lembrete'),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.request and self.request.user.is_authenticated:
            instance.usuario = self.request.user
        if commit:
            instance.save()
        return instance
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Validação customizada pode ser adicionada aqui
        prazo = cleaned_data.get('prazo')
        data_inicio = cleaned_data.get('data_inicio')
        
        if prazo and data_inicio and prazo < data_inicio:
            self.add_error('prazo', ('O prazo não pode ser anterior à data de início'))
        
        return cleaned_data

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adicione um comentário...'
            }),
        }


