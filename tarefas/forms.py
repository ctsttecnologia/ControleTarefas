
from datetime import timedelta
import os
from django import forms
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import DurationField

from tarefas.admin import Comentario
from .models import Tarefas, Comentario, User

from dateutil.relativedelta import relativedelta



class TarefaForm(forms.ModelForm):
    # Campos para a funcionalidade de recorrência
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
        widget=forms.DateInput(attrs={'class': 'form-control date-picker', 'type': 'date'})
    )

    class Meta:
        model = Tarefas
        fields = [
            'titulo', 'descricao', 'status', 'prioridade',
            'data_inicio', 'prazo', 'responsavel', 'projeto',
            'duracao_prevista', 'tempo_gasto', 'dias_lembrete',
            'recorrente', 'frequencia_recorrencia', 'data_fim_recorrencia'
        ]
        widgets = {
            'data_inicio': forms.DateTimeInput(
                attrs={
                    'class': 'form-control datetime-picker', # AQUI ADICIONAMOS A CLASSE!
                    'placeholder': 'Selecione a data e hora de início'
                }
            ),
            'prazo': forms.DateTimeInput(
                attrs={
                    'class': 'form-control datetime-picker', # Aproveite para adicionar no prazo também
                    'placeholder': 'Selecione o prazo final'
                }
            ),
            # Adicione outros widgets para estilização se desejar
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'projeto': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
            'duracao_prevista': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex: 1 02:30:00'}),
            'tempo_gasto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex: 0 01:15:00'}),
            'dias_lembrete': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
        }
        help_texts = {
            'duracao_prevista': 'Formato: dias HH:MM:SS (ex: 1 02:30:00)',
            'tempo_gasto': 'Formato: dias HH:MM:SS',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['recorrente'].initial = self.instance.recorrente
            self.fields['frequencia_recorrencia'].initial = self.instance.frequencia_recorrencia
            self.fields['data_fim_recorrencia'].initial = self.instance.data_fim_recorrencia
            self.fields['data_inicio'].disabled = True
            self.fields['data_inicio'].help_text = 'Data de início não pode ser alterada após criação.'

        if self.request and hasattr(self.request.user, 'equipe'):
            self.fields['responsavel'].queryset = User.objects.filter(equipe=self.request.user.equipe)

        for field_name, field in self.fields.items():
            if self.errors.get(field_name):
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_classes} is-invalid'.strip()

    def clean(self):
        cleaned_data = super().clean()
        dias_lembrete = cleaned_data.get('dias_lembrete')
        prazo = cleaned_data.get('prazo')
        recorrente = cleaned_data.get('recorrente')
        frequencia = cleaned_data.get('frequencia_recorrencia')
        data_fim = cleaned_data.get('data_fim_recorrencia')

        if dias_lembrete and not prazo:
            raise forms.ValidationError(
                {'dias_lembrete': 'Para definir dias de lembrete, você precisa primeiro definir um "Prazo Final".'}
            )

        if recorrente and (not frequencia or not data_fim):
            raise forms.ValidationError(
                "Se a tarefa é recorrente, a frequência e a data final da recorrência são obrigatórias."
            )

        prazo = cleaned_data.get('prazo')
        data_inicio = cleaned_data.get('data_inicio')

        if prazo and data_inicio and prazo < data_inicio:
            self.add_error('prazo', "O prazo final não pode ser anterior à data de início.")

        return cleaned_data

    def save(self, commit=True):
        # O método save fica MUITO mais simples agora!
        instance = super().save(commit=False)

        if not instance.pk and self.request and self.request.user.is_authenticated:
            instance.usuario = self.request.user
        
        if self.request and self.request.user.is_authenticated:
            instance._user = self.request.user

        # Transfere os dados dos campos de formulário para os campos do modelo
        instance.recorrente = self.cleaned_data.get('recorrente', False)
        instance.frequencia_recorrencia = self.cleaned_data.get('frequencia_recorrencia')
        instance.data_fim_recorrencia = self.cleaned_data.get('data_fim_recorrencia')

        if commit:
            instance.save() # O método save() do MODELO agora faz todo o trabalho pesado
            self.save_m2m()
            
        return instance

    def _criar_proxima_recorrencia(self, tarefa_atual):
        """Cria a próxima ocorrência de uma tarefa recorrente."""
        if not tarefa_atual.recorrente or not tarefa_atual.data_fim_recorrencia:
            return

        # Verifica se a data final da recorrência já passou
        if timezone.now().date() >= tarefa_atual.data_fim_recorrencia:
            return

        # Calcula o intervalo da próxima tarefa
        frequencia = tarefa_atual.frequencia_recorrencia
        if frequencia == 'diaria': delta = relativedelta(days=1)
        elif frequencia == 'semanal': delta = relativedelta(weeks=1)
        elif frequencia == 'quinzenal': delta = relativedelta(weeks=2)
        elif frequencia == 'mensal': delta = relativedelta(months=1)
        else: return

        # Calcula as novas datas
        novo_inicio = tarefa_atual.data_inicio + delta
        novo_prazo = (tarefa_atual.prazo + delta) if tarefa_atual.prazo else None
        
        # Para a criação se a nova data de início ultrapassar o fim da recorrência
        if novo_inicio.date() > tarefa_atual.data_fim_recorrencia:
            return

        # Cria a nova tarefa copiando os dados da atual
        Tarefas.objects.create(
            titulo=tarefa_atual.titulo,
            descricao=tarefa_atual.descricao,
            prioridade=tarefa_atual.prioridade,
            responsavel=tarefa_atual.responsavel,
            projeto=tarefa_atual.projeto,
            usuario=tarefa_atual.usuario,
            status='pendente', # A nova tarefa começa como pendente
            data_inicio=novo_inicio,
            prazo=novo_prazo,
            duracao_prevista=tarefa_atual.duracao_prevista,
            # Mantém os dados da recorrência
            recorrente=True,
            frequencia_recorrencia=tarefa_atual.frequencia_recorrencia,
            data_fim_recorrencia=tarefa_atual.data_fim_recorrencia,
            # Vincula à tarefa original
            tarefa_pai=tarefa_atual.tarefa_pai or tarefa_atual,
        )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Preenche os campos de recorrência se a instância já existir
        if self.instance and self.instance.pk:
            self.fields['recorrente'].initial = self.instance.recorrente
            self.fields['frequencia_recorrencia'].initial = self.instance.frequencia_recorrencia
            self.fields['data_fim_recorrencia'].initial = self.instance.data_fim_recorrencia

        for field_name, field in self.fields.items():
            if self.errors.get(field_name):
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_classes} is-invalid'.strip()

    def clean(self):
        cleaned_data = super().clean()
        recorrente = cleaned_data.get('recorrente')
        frequencia = cleaned_data.get('frequencia_recorrencia')
        data_fim = cleaned_data.get('data_fim_recorrencia')

        if recorrente and (not frequencia or not data_fim):
            raise forms.ValidationError(
                "Se a tarefa é recorrente, a frequência e a data final da recorrência são obrigatórias."
            )
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Define o criador da tarefa se for uma nova instância
        if not instance.pk and self.request and self.request.user.is_authenticated:
            instance.usuario = self.request.user
        
        # Anexa o usuário para o log de histórico
        if self.request and self.request.user.is_authenticated:
            instance._user = self.request.user

        # Lógica para criar a próxima recorrência
        status_anterior = self.initial.get('status')
        novo_status = self.cleaned_data.get('status')
        
        if status_anterior != 'concluida' and novo_status == 'concluida':
            self._criar_proxima_recorrencia(instance)
            
        if commit:
            instance.save()
            
        return instance

    def _criar_proxima_recorrencia(self, tarefa_atual):
        """Cria a próxima ocorrência de uma tarefa recorrente."""
        if not tarefa_atual.recorrente or not tarefa_atual.data_fim_recorrencia:
            return

        # Verifica se a data final da recorrência já passou
        if timezone.now().date() >= tarefa_atual.data_fim_recorrencia:
            return

        # Calcula o intervalo da próxima tarefa
        frequencia = tarefa_atual.frequencia_recorrencia
        if frequencia == 'diaria': delta = relativedelta(days=1)
        elif frequencia == 'semanal': delta = relativedelta(weeks=1)
        elif frequencia == 'quinzenal': delta = relativedelta(weeks=2)
        elif frequencia == 'mensal': delta = relativedelta(months=1)
        else: return

        # Calcula as novas datas
        novo_inicio = tarefa_atual.data_inicio + delta
        novo_prazo = (tarefa_atual.prazo + delta) if tarefa_atual.prazo else None
        
        # Para a criação se a nova data de início ultrapassar o fim da recorrência
        if novo_inicio.date() > tarefa_atual.data_fim_recorrencia:
            return

        # Cria a nova tarefa copiando os dados da atual
        Tarefas.objects.create(
            titulo=tarefa_atual.titulo,
            descricao=tarefa_atual.descricao,
            prioridade=tarefa_atual.prioridade,
            responsavel=tarefa_atual.responsavel,
            projeto=tarefa_atual.projeto,
            usuario=tarefa_atual.usuario,
            status='pendente', # A nova tarefa começa como pendente
            data_inicio=novo_inicio,
            prazo=novo_prazo,
            duracao_prevista=tarefa_atual.duracao_prevista,
            # Mantém os dados da recorrência
            recorrente=True,
            frequencia_recorrencia=tarefa_atual.frequencia_recorrencia,
            data_fim_recorrencia=tarefa_atual.data_fim_recorrencia,
            # Vincula à tarefa original
            tarefa_pai=tarefa_atual.tarefa_pai or tarefa_atual,
        )
        
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

