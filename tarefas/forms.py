
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
            'data_inicio', 'prazo', 'responsavel', 'participantes', 'projeto',
            'duracao_prevista', 'tempo_gasto', 'dias_lembrete',
            'recorrente', 'frequencia_recorrencia', 'data_fim_recorrencia','ata_reuniao',
        ]
        widgets = {
            'data_inicio': forms.DateTimeInput(
                attrs={
                    'class': 'form-control datetime-picker', # AQUI ADICIONAMOS A CLASSE!
                    'placeholder': 'Selecione a data e hora de início',
                    'ata_reuniao': forms.Select(attrs={'class': 'form-control select2-widget'}),
                }
            ),
            'prazo': forms.DateTimeInput(
                attrs={
                    'class': 'form-control datetime-picker', # Aproveite para adicionar no prazo também
                    'placeholder': 'Selecione o prazo final'
                }
            ),
            'participantes': forms.SelectMultiple(
                attrs={
                    'class': 'form-control',
                    
                }
            ),
            # Adicione outros widgets para estilização se desejar
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'projeto': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'duracao_prevista': 'Formato: dias HH:MM:SS (ex: 1 02:30:00)',
            'tempo_gasto': 'Formato: dias HH:MM:SS',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Tenta pegar o queryset já filtrado do campo 'responsavel'
        try:
            # Pega a lista de usuários do campo 'responsavel'
            user_queryset = self.fields['responsavel'].queryset
        except KeyError:
            # Se 'responsavel' não estiver no form, cria um queryset padrão
            user_queryset = User.objects.filter(is_active=True)

        # Aplica o mesmo queryset ao campo 'participantes'
        self.fields['participantes'].queryset = user_queryset

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
        # A linha abaixo para obter o 'request' já está no seu código e deve ser mantida
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # --- LÓGICA CORRIGIDA E ADICIONADA ---
        # Verifica se o formulário está sendo usado para editar uma instância existente
        if self.instance and self.instance.pk:
            # 1. Pega os valores de recorrência salvos no modelo...
            # ...e os define como os valores iniciais dos campos do formulário.
            self.fields['recorrente'].initial = self.instance.recorrente
            self.fields['frequencia_recorrencia'].initial = self.instance.frequencia_recorrencia
            self.fields['data_fim_recorrencia'].initial = self.instance.data_fim_recorrencia

            # 2. Desabilita a edição da data de início para tarefas existentes
            self.fields['data_inicio'].disabled = True
            self.fields['data_inicio'].help_text = 'Data de início não pode ser alterada após a criação.'

        # Filtra a lista de responsáveis para mostrar apenas usuários da mesma equipe (se aplicável)
        # Esta parte do seu código já estava correta.
        if self.request and hasattr(self.request.user, 'equipe'):
            self.fields['responsavel'].queryset = User.objects.filter(
                equipe=self.request.user.equipe
            )

        # Adiciona a classe 'is-invalid' aos campos que tiverem erros de validação
        for field_name, field in self.fields.items():
            if self.errors.get(field_name):
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_classes} is-invalid'.strip()
   
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


