# gestao_riscos/forms.py

from django import forms
from .models import Incidente, Inspecao
from django.contrib.auth import get_user_model

class IncidenteForm(forms.ModelForm):
    """
    Formulário para criar e editar um Incidente.
    Ele é gerado automaticamente a partir do modelo Incidente.
    """
    class Meta:
        model = Incidente
        # Define os campos do modelo que aparecerão no formulário
        fields = [
            'descricao', 
            'detalhes', 
            'setor', 
            'tipo_incidente', 
            'data_ocorrencia'
        ]
        
        # O campo 'registrado_por' será preenchido automaticamente na view,
        # por isso não o incluímos na lista de 'fields'.
        
        # Personaliza os widgets para melhor usabilidade e estilo com Bootstrap
        widgets = {
            'descricao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Quase queda de material da prateleira'
            }),
            'detalhes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Descreva em detalhes o que aconteceu, pessoas envolvidas e ações tomadas.'
            }),
            'setor': forms.Select(attrs={'class': 'form-select'}),
            'tipo_incidente': forms.Select(attrs={'class': 'form-select'}),
            'data_ocorrencia': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local' # Usa o seletor de data/hora do navegador
                },
                format='%Y-%m-%dT%H:%M'
            ),
        }
        
        # Personaliza os rótulos (labels) dos campos, se desejar
        labels = {
            'descricao': 'Título do Incidente',
            'detalhes': 'Descrição Detalhada',
            'data_ocorrencia': 'Data e Hora da Ocorrência',
        }

class InspecaoForm(forms.ModelForm):
    """
    Formulário para agendar uma nova Inspeção.
    """
    class Meta:
        model = Inspecao
        # Campos que o usuário irá preencher ao agendar
        fields = [
            'equipamento',
            'data_agendada',
            'inspetor',
            'observacoes',
        ]

        # Os campos 'status' e 'data_realizacao' não são incluídos,
        # pois o status inicial é sempre 'PENDENTE' e a data de realização
        # será preenchida quando a inspeção for concluída.

        widgets = {
            'equipamento': forms.Select(attrs={'class': 'form-select'}),
            'data_agendada': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date' # Usa o seletor de data do navegador
                }
            ),
            'inspetor': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Alguma observação ou instrução para a inspeção?'
                }
            ),
        }
        labels = {
            'equipamento': 'Equipamento a ser Inspecionado',
            'data_agendada': 'Data de Agendamento da Inspeção',
            'inspetor': 'Inspetor Responsável',
            'observacoes': 'Observações (Opcional)',
        }

    # Dica de Otimização: Se você tiver muitos usuários, o campo 'inspetor'
    # ficará enorme. Você pode filtrar para mostrar apenas usuários de um
    # grupo específico (ex: 'Técnicos de Segurança').
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exemplo de como filtrar o campo 'inspetor'
        # self.fields['inspetor'].queryset = get_user_model().objects.filter(groups__name='Técnicos de Segurança')

