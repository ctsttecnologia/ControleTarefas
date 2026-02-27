
# tarefas/forms.py

import os
from django import forms
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Tarefas, Comentario

User = get_user_model()


class TarefaForm(forms.ModelForm):
    """Formulário unificado para criação e edição de Tarefas."""

    recorrente = forms.BooleanField(
        required=False,
        label="Tornar esta tarefa recorrente?",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    frequencia_recorrencia = forms.ChoiceField(
        choices=[('', '---------')] + Tarefas.FREQUENCIA_CHOICES,
        required=False,
        label="Repetir a cada",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    data_fim_recorrencia = forms.DateField(
        required=False,
        label="Repetir até a data",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = Tarefas
        fields = [
            'titulo', 'descricao', 'status', 'prioridade',
            'data_inicio', 'prazo', 'responsavel', 'participantes',
            'projeto', 'duracao_prevista', 'tempo_gasto',
            'dias_lembrete', 'recorrente', 'frequencia_recorrencia',
            'data_fim_recorrencia', 'ata_reuniao',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
            'data_inicio': forms.DateTimeInput(attrs={
                'class': 'form-control datetime-picker',
                'placeholder': 'Data e hora de início'
            }),
            'prazo': forms.DateTimeInput(attrs={
                'class': 'form-control datetime-picker',
                'placeholder': 'Prazo final'
            }),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'participantes': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'projeto': forms.TextInput(attrs={'class': 'form-control'}),
            'ata_reuniao': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'duracao_prevista': 'Formato: dias HH:MM:SS (ex: 1 02:30:00)',
            'tempo_gasto': 'Formato: dias HH:MM:SS',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Filtra usuários ativos para campos de responsável e participantes
        user_qs = User.objects.filter(is_active=True)

        # Se usuário pertence a uma equipe, filtra pela equipe
        if self.request and hasattr(self.request.user, 'equipe') and self.request.user.equipe:
            user_qs = user_qs.filter(equipe=self.request.user.equipe)

        self.fields['responsavel'].queryset = user_qs
        self.fields['participantes'].queryset = user_qs

        # Preenche campos de recorrência para edição
        if self.instance and self.instance.pk:
            self.fields['recorrente'].initial = self.instance.recorrente
            self.fields['frequencia_recorrencia'].initial = self.instance.frequencia_recorrencia
            self.fields['data_fim_recorrencia'].initial = self.instance.data_fim_recorrencia
            # Desabilita data_inicio em edição
            self.fields['data_inicio'].disabled = True
            self.fields['data_inicio'].help_text = 'Não pode ser alterada após criação.'

        # Adiciona classe is-invalid aos campos com erro
        for field_name in self.errors:
            if field_name in self.fields:
                widget = self.fields[field_name].widget
                existing_classes = widget.attrs.get('class', '')
                widget.attrs['class'] = f'{existing_classes} is-invalid'.strip()

    def clean(self):
        cleaned_data = super().clean()
        prazo = cleaned_data.get('prazo')
        data_inicio = cleaned_data.get('data_inicio')
        dias_lembrete = cleaned_data.get('dias_lembrete')
        recorrente = cleaned_data.get('recorrente')
        frequencia = cleaned_data.get('frequencia_recorrencia')
        data_fim = cleaned_data.get('data_fim_recorrencia')

        # Validação: lembrete requer prazo
        if dias_lembrete and not prazo:
            self.add_error(
                'dias_lembrete',
                'Para definir dias de lembrete, defina um "Prazo Final".'
            )

        # Validação: prazo após data de início
        if prazo and data_inicio and prazo < data_inicio:
            self.add_error('prazo', 'O prazo não pode ser anterior à data de início.')

        # Validação: recorrência requer frequência e data fim
        if recorrente and (not frequencia or not data_fim):
            raise forms.ValidationError(
                'Se a tarefa é recorrente, frequência e data final são obrigatórias.'
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Define criador se for nova tarefa
        if not instance.pk and self.request and self.request.user.is_authenticated:
            instance.usuario = self.request.user

        # Anexa usuário para histórico
        if self.request and self.request.user.is_authenticated:
            instance._user = self.request.user

        # Transfere dados de recorrência
        instance.recorrente = self.cleaned_data.get('recorrente', False)
        instance.frequencia_recorrencia = self.cleaned_data.get('frequencia_recorrencia')
        instance.data_fim_recorrencia = self.cleaned_data.get('data_fim_recorrencia')

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class ComentarioForm(forms.ModelForm):
    """Formulário para comentários em tarefas."""

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
            if anexo.size > Comentario.TAMANHO_MAXIMO_ANEXO:
                raise forms.ValidationError(
                    f'Tamanho máximo: {Comentario.TAMANHO_MAXIMO_ANEXO // (1024 * 1024)}MB'
                )
        return anexo


