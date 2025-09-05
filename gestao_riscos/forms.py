# gestao_riscos/forms.py
from django import forms
from django.contrib.auth import get_user_model
from seguranca_trabalho.models import Equipamento
from .models import Incidente, Inspecao, CartaoTag
from departamento_pessoal.models import Funcionario

User = get_user_model()

class IncidenteForm(forms.ModelForm):
    """Formulário para criar e editar um Incidente."""
    class Meta:
        model = Incidente
        fields = ['descricao', 'detalhes', 'setor', 'tipo_incidente', 'data_ocorrencia']
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
            'descricao': 'Título do Incidente', 'detalhes': 'Descrição Detalhada',
            'data_ocorrencia': 'Data e Hora da Ocorrência',
        }

class InspecaoForm(forms.ModelForm):
    """Formulário para agendar Inspeção, com filtros de filial baseados na sessão."""
    
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request:
            filial_id = request.session.get('active_filial_id')
            if filial_id:
                # Filtra o dropdown de equipamentos (isso deve estar correto)
                self.fields['equipamento'].queryset = Equipamento.objects.filter(filial_id=filial_id)
                # O modelo User não tem 'filial_id', mas sim 'filial_ativa_id'.
                self.fields['inspetor'].queryset = User.objects.filter(filial_ativa_id=filial_id)

    class Meta:
        model = Inspecao
        fields = ['equipamento', 'data_agendada', 'inspetor', 'observacoes']
        widgets = {
            'equipamento': forms.Select(attrs={'class': 'form-select'}),
            'data_agendada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'inspetor': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Alguma observação ou instrução para a inspeção?'}
            ),
        }
        labels = {
            'equipamento': 'Equipamento a ser Inspecionado', 'data_agendada': 'Data de Agendamento',
            'inspetor': 'Inspetor Responsável', 'observacoes': 'Observações (Opcional)',
        }

class CartaoTagForm(forms.ModelForm):
    """Formulário para criar e editar Cartões de Bloqueio."""

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request:
            filial_id = request.session.get('active_filial_id')
            if filial_id:
                # Filtra o campo 'funcionário' para mostrar apenas os da filial ativa
                self.fields['funcionario'].queryset = Funcionario.objects.filter(filial_id=filial_id)

    class Meta:
        model = CartaoTag
        fields = ['funcionario', 'fone', 'data_validade', 'ativo']
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
            'fone': forms.TextInput(attrs={'class': 'form-control'}),
            'data_validade': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


