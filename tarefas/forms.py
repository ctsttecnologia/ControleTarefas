
from datetime import timedelta
import os
from django import forms
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import DurationField

from tarefas.admin import Comentario
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
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'prioridade': forms.Select(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateTimeInput(
                attrs={'class': 'form-control datetime-picker'},
                format='%Y-%m-%dT%H:%M'
            ),
            'prazo': forms.DateTimeInput(
                attrs={'class': 'form-control datetime-picker'},
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
                attrs={'class': 'form-control datetime-picker'},
                format='%Y-%m-%dT%H:%M'
            ),
        }
        
        help_texts = {
            'duracao_prevista': 'Formato: dias HH:MM:SS (ex: 1 02:30:00 para 1 dia e 2 horas e 30 minutos)',
            'tempo_gasto': 'Formato: dias HH:MM:SS',
        }

class TarefaForm(forms.ModelForm):
    # ... (sua class Meta e outros métodos continuam iguais) ...
    # modelo e quais campos ele está associado.
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
            'status': forms.Select(attrs={'class': 'form-select'}), # Usar form-select para consistência com Bootstrap
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
            'data_inicio': forms.DateTimeInput(
                attrs={'class': 'form-control datetime-picker'},
                format='%Y-%m-%dT%H:%M'
            ),
            'prazo': forms.DateTimeInput(
                attrs={'class': 'form-control datetime-picker'},
                format='%Y-%m-%dT%H:%M'
            ),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'projeto': forms.TextInput(attrs={'class': 'form-control'}),
            'duracao_prevista': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD HH:MM:SS'}),
            'tempo_gasto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD HH:MM:SS'}),
            'dias_lembrete': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
            'data_lembrete': forms.DateTimeInput(
                attrs={'class': 'form-control datetime-picker'},
                format='%Y-%m-%dT%H:%M'
            ),
        }
        help_texts = {
            'duracao_prevista': 'Formato: dias HH:MM:SS (ex: 1 02:30:00 para 1 dia, 2 horas e 30 minutos)',
            'tempo_gasto': 'Formato: dias HH:MM:SS',
        }
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Lógica para desabilitar campo em edição
        if self.instance and self.instance.pk:
            self.fields['data_inicio'].disabled = True
            self.fields['data_inicio'].help_text = 'Data de início não pode ser alterada após criação'

        # Filtra responsáveis da mesma equipe se houver
        if self.request and hasattr(self.request.user, 'equipe'):
            self.fields['responsavel'].queryset = User.objects.filter(
                equipe=self.request.user.equipe
            )

        # >>> INÍCIO DA NOVA LÓGICA PARA ESTILIZAR ERROS <<<
        # Itera sobre todos os campos do formulário
        for field_name, field in self.fields.items():
            # Verifica se este campo específico tem erros
            if self.errors.get(field_name):
                # Pega as classes CSS existentes no widget
                existing_classes = field.widget.attrs.get('class', '')
                # Adiciona a classe 'is-invalid' do Bootstrap
                field.widget.attrs['class'] = f'{existing_classes} is-invalid'.strip()
 

    def save(self, commit=True):
        instance = super().save(commit=False)
        # LÓGICA CRÍTICA: Se for uma nova tarefa, define o criador como o usuário logado.
        if not instance.pk and self.request and self.request.user.is_authenticated:
            instance.usuario = self.request.user
        
        # Anexa o usuário que está fazendo a alteração para usar no método save() do modelo
        if self.request and self.request.user.is_authenticated:
            instance._user = self.request.user

        if commit:
            instance.save() # Agora salva no banco com o usuário já definido
            
        return instance
    
    def clean_prazo(self):
        """Validação para garantir que o prazo não seja anterior à data de início."""
        prazo = self.cleaned_data.get('prazo')
        data_inicio = self.cleaned_data.get('data_inicio')

        if prazo and data_inicio and prazo < data_inicio:
            raise forms.ValidationError("O prazo final não pode ser anterior à data de início.")
        return prazo
    
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


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto', 'anexo']
        widgets = {
            'texto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Escreva seu comentário...'
            }),
            'anexo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_anexo(self):
        anexo = self.cleaned_data.get('anexo')
        if anexo:
            # CORREÇÃO: Usando a constante do modelo Comentario, não do ComentarioAdmin
            if anexo.size > Comentario.TAMANHO_MAXIMO_ANEXO:
                raise forms.ValidationError(
                    f'Tamanho máximo permitido: {Comentario.TAMANHO_MAXIMO_ANEXO // (1024*1024)}MB'
                )
        return anexo

