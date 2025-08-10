# gestao_riscos/forms.py
from django import forms
from .models import Incidente, Inspecao, User

# Supondo que o modelo Equipamento está em outro app
from seguranca_trabalho.models import Equipamento 

class IncidenteForm(forms.ModelForm):
    """Formulário para criar e editar um Incidente."""
    class Meta:
        model = Incidente
        # Os campos 'filial' e 'registrado_por' são preenchidos na view
        fields = [
            'descricao', 
            'detalhes', 
            'setor', 
            'tipo_incidente', 
            'data_ocorrencia'
        ]
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Quase queda de material da prateleira'}),
            'detalhes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descreva em detalhes o que aconteceu...'}),
            'setor': forms.Select(attrs={'class': 'form-select'}),
            'tipo_incidente': forms.Select(attrs={'class': 'form-select'}),
            'data_ocorrencia': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
        }
        labels = {
            'descricao': 'Título do Incidente',
            'detalhes': 'Descrição Detalhada',
            'data_ocorrencia': 'Data e Hora da Ocorrência',
        }

class InspecaoForm(forms.ModelForm):
    """Formulário para agendar uma nova Inspeção, com filtros de filial."""
    
    def __init__(self, *args, **kwargs):
        # Remove a keyword 'user' antes de chamar o super(), pois o ModelForm não a espera.
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Se um usuário foi passado (da view), filtramos os campos.
        if user and hasattr(user, 'inspecoes'):
            filial_usuario = user.filial
            # Filtra o campo 'equipamento' para mostrar apenas os da filial do usuário.
            self.fields['equipamento'].queryset = Equipamento.objects.filter(filial=filial_usuario)
            # Filtra o campo 'inspetor' para mostrar apenas usuários da mesma filial.
            self.fields['inspetor'].queryset = User.objects.filter(filial=filial_usuario)

    class Meta:
        model = Inspecao
        # O campo 'filial' será preenchido automaticamente na view.
        fields = [
            'equipamento',
            'data_agendada',
            'inspetor',
            'observacoes',
        ]
        widgets = {
            'equipamento': forms.Select(attrs={'class': 'form-select'}),
            'data_agendada': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'inspetor': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Alguma observação ou instrução para a inspeção?'}
            ),
        }
        labels = {
            'equipamento': 'Equipamento a ser Inspecionado',
            'data_agendada': 'Data de Agendamento',
            'inspetor': 'Inspetor Responsável',
            'observacoes': 'Observações (Opcional)',
        }
