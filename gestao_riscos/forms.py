# gestao_riscos/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import Incidente, Inspecao, CartaoTag
from departamento_pessoal.models import Funcionario
from seguranca_trabalho.models import Equipamento, EntregaEPI


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
    """
        Filtra os querysets para os campos 'responsavel' e 'equipamento'
        com base na filial do usuário logado.
    """
    def __init__(self, *args, **kwargs):

        self.request = kwargs.pop('request', None)
        super(InspecaoForm, self).__init__(*args, **kwargs)

        if self.request and self.request.user.is_authenticated:

            filial_usuario = self.request.user.filial_ativa
            
            if 'responsavel' in self.fields:
                # Filtra para mostrar apenas usuários da mesma filial
                self.fields['responsavel'].queryset = User.objects.filter(filial_ativa=filial_usuario, is_active=True)
            
            if 'equipamento' in self.fields:
                # Filtra para mostrar apenas equipamentos da mesma filial
                self.fields['equipamento'].queryset = Equipamento.objects.filter(filial=filial_usuario, ativo=True)
                
            if 'entrega_epi' in self.fields:
                 # Filtra para mostrar apenas entregas da mesma filial
                self.fields['entrega_epi'].queryset = EntregaEPI.objects.filter(filial=filial_usuario)
    class Meta:
        model = Inspecao
        fields = ['equipamento', 'entrega_epi', 'data_agendada', 'responsavel', 'observacoes', 'status', 'data_realizacao',]
        widgets = {
            'equipamento': forms.Select(attrs={'class': 'form-select'}),
            'data_agendada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_realizacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Alguma observação ou instrução para a inspeção?'}
            ),
        }
        labels = {
            'equipamento': 'Equipamento a ser Inspecionado', 'data_agendada': 'Data de Agendamento',
            'responsavel': 'Inspetor Responsável', 'observacoes': 'Observações (Opcional)',
        }

    def clean(self):
        """
        Garante que 'equipamento' ou 'entrega_epi' seja preenchido.
        """
        cleaned_data = super().clean()
        equipamento = cleaned_data.get('equipamento')
        entrega_epi = cleaned_data.get('entrega_epi')

        if not equipamento and not entrega_epi:
            raise forms.ValidationError(
                "A inspeção deve estar ligada a um 'Equipamento' genérico ou a um 'Item de EPI Específico'."
            )
        return cleaned_data

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

            # Adicione filtros para 'cargo' se necessário
            if 'cargo' in self.fields:
                self.fields['cargo'].queryset = self.fields['cargo'].queryset.filter(
                    filial=filial_id
                )

    class Meta:
        model = CartaoTag
        fields = ['funcionario', 'cargo', 'fone', 'data_validade', 'ativo']
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'fone': forms.TextInput(attrs={'class': 'form-control'}),
            'data_validade': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


