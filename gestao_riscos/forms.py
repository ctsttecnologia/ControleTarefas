# gestao_riscos/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import Incidente, Inspecao, CartaoTag
from departamento_pessoal.models import Funcionario
from seguranca_trabalho.models import Equipamento, EntregaEPI
from .models import TipoRisco


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
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(InspecaoForm, self).__init__(*args, **kwargs)

        if self.request and self.request.user.is_authenticated:
            filial_usuario = self.request.user.filial_ativa

            if 'responsavel' in self.fields:
                self.fields['responsavel'].queryset = User.objects.filter(
                    filial_ativa=filial_usuario, is_active=True
                )

            if 'equipamento' in self.fields:
                # ✅ Equipamento filtra Equipamento (não EntregaEPI!)
                self.fields['equipamento'].queryset = Equipamento.objects.filter(
                    filial=filial_usuario, ativo=True
                )

            if 'entrega_epi' in self.fields:
                self.fields['entrega_epi'].required = False
                self.fields['entrega_epi'].label = 'Item de EPI Específico (opcional)'

                # ✅ Sem "status='ativo'" — EntregaEPI não tem campo status
                # Usa data_devolucao__isnull=True para filtrar apenas os não devolvidos
                if self.data and self.data.get('equipamento'):
                    try:
                        equip_id = int(self.data.get('equipamento'))
                        self.fields['entrega_epi'].queryset = EntregaEPI.objects.filter(
                            filial=filial_usuario,
                            equipamento_id=equip_id,
                            data_devolucao__isnull=True  # ← Não devolvido = "ativo"
                        )
                    except (ValueError, TypeError):
                        self.fields['entrega_epi'].queryset = EntregaEPI.objects.none()
                elif self.instance and self.instance.pk and self.instance.equipamento:
                    self.fields['entrega_epi'].queryset = EntregaEPI.objects.filter(
                        filial=filial_usuario,
                        equipamento=self.instance.equipamento,
                        data_devolucao__isnull=True
                    )
                else:
                    self.fields['entrega_epi'].queryset = EntregaEPI.objects.none()

    class Meta:
        model = Inspecao
        fields = ['equipamento', 'entrega_epi', 'data_agendada', 'responsavel', 'observacoes', 'status', 'data_realizacao']
        widgets = {
            'equipamento': forms.Select(attrs={'class': 'form-select', 'id': 'id_equipamento'}),
            'entrega_epi': forms.Select(attrs={'class': 'form-select', 'id': 'id_entrega_epi'}),
            'data_agendada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_realizacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Alguma observação ou instrução para a inspeção?'}
            ),
        }
        labels = {
            'equipamento': 'Equipamento a ser Inspecionado',
            'entrega_epi': 'Item de EPI Específico (opcional)',
            'data_agendada': 'Data de Agendamento',
            'responsavel': 'Inspetor Responsável',
            'observacoes': 'Observações (Opcional)',
        }

    def clean(self):
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

class TipoRiscoForm(forms.ModelForm):
    """Formulário de Tipo de Risco"""

    class Meta:
        model = TipoRisco
        fields = ['categoria', 'nome', 'descricao', 'codigo_cor', 'nr_referencia', 'ativo']
        widgets = {
            'categoria': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_categoria',
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Ruído, Poeira, Vírus, etc.',
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição detalhada do tipo de risco...',
            }),
            'codigo_cor': forms.TextInput(attrs={
                'class': 'form-control form-control-color',
                'type': 'color',
                'style': 'width: 80px; height: 40px; padding: 2px;',
            }),
            'nr_referencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: NR-15, NR-17',
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.filial = kwargs.pop('filial', None)
        super().__init__(*args, **kwargs)

        # Labels mais amigáveis
        self.fields['categoria'].label = 'Categoria do Risco'
        self.fields['nome'].label = 'Nome do Risco / Agente'
        self.fields['codigo_cor'].label = 'Cor Identificadora'
        self.fields['nr_referencia'].label = 'NR de Referência'

    def clean(self):
        cleaned_data = super().clean()
        categoria = cleaned_data.get('categoria')
        nome = cleaned_data.get('nome')

        if categoria and nome and self.filial:
            qs = TipoRisco.objects.filter(
                categoria=categoria,
                nome__iexact=nome,
                filial=self.filial
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'Já existe o risco "{nome}" na categoria "{self.instance.get_categoria_display() if self.instance.pk else dict(TipoRisco.CATEGORIA_RISCO_CHOICES).get(categoria, categoria)}" para esta filial.'
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.filial and not instance.filial_id:
            instance.filial = self.filial
        if commit:
            instance.save()
        return instance

