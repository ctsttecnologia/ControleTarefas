
# =============================================================================
# gestao_riscos/forms.py
# =============================================================================
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.utils import get_filial_ativa
from departamento_pessoal.models import Cargo, Funcionario
from seguranca_trabalho.models import EntregaEPI, Equipamento

from .models import (
    CATEGORIA_RISCO_CHOICES, TIPO_OCORRENCIA_CHOICES,
    CartaoTag, Incidente, Inspecao, TipoRisco,
)

UserModel = get_user_model()

CAMPOS_SAUDE = ('parte_corpo_atingida', 'dias_afastamento', 'cat_emitida', 'numero_cat')


class FilialFormMixin:
    """Resolve a filial ativa a partir do request (fonte única: core.utils)."""

    def _pop_filial(self, kwargs):
        request = kwargs.pop('request', None)
        self.request = request
        self.filial = (
            get_filial_ativa(request.user, request)
            if request and request.user.is_authenticated else None
        )


class IncidenteForm(FilialFormMixin, forms.ModelForm):
    tipo_ocorrencia = forms.ChoiceField(
        choices=TIPO_OCORRENCIA_CHOICES, label='Tipo de Ocorrência',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_ocorrencia'}),
    )

    class Meta:
        model = Incidente
        fields = [
            'tipo_ocorrencia', 'gravidade', 'descricao', 'detalhes', 'setor',
            'local_especifico', 'data_ocorrencia', 'funcionario_envolvido',
            'parte_corpo_atingida', 'dias_afastamento', 'cat_emitida', 'numero_cat',
            'acao_imediata',
        ]
        widgets = {
            'gravidade': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 255,
                                                'placeholder': 'Ex: Queda de material no setor de produção'}),
            'detalhes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                              'placeholder': 'Descreva o que aconteceu, como e por quê...'}),
            'setor': forms.Select(attrs={'class': 'form-select'}),
            'local_especifico': forms.TextInput(attrs={'class': 'form-control',
                                                       'placeholder': 'Ex: Galpão 2, próximo à empilhadeira'}),
            'data_ocorrencia': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'},
                                                   format='%Y-%m-%dT%H:%M'),
            'funcionario_envolvido': forms.Select(attrs={'class': 'form-select'}),
            'parte_corpo_atingida': forms.TextInput(attrs={'class': 'form-control',
                                                           'placeholder': 'Ex: Mão direita, Coluna lombar'}),
            'dias_afastamento': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 3650}),
            'cat_emitida': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'numero_cat': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nº da CAT'}),
            'acao_imediata': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                   'placeholder': 'Primeiros socorros, isolamento da área, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        self._pop_filial(kwargs)
        super().__init__(*args, **kwargs)
        self.fields['funcionario_envolvido'].queryset = (
            Funcionario.objects.filter(filial=self.filial, status='ATIVO')
            .only('id', 'nome_completo').order_by('nome_completo')
            if self.filial else Funcionario.objects.none()
        )

    def clean_data_ocorrencia(self):
        data = self.cleaned_data.get('data_ocorrencia')
        if data and data > timezone.now():
            raise forms.ValidationError('A data da ocorrência não pode estar no futuro.')
        return data

    def clean(self):
        cd = super().clean()
        tipo = cd.get('tipo_ocorrencia') or ''
        is_acidente = tipo.startswith('ACIDENTE')

        if is_acidente and not cd.get('funcionario_envolvido'):
            self.add_error('funcionario_envolvido', 'Funcionário envolvido é obrigatório para acidentes.')
        if cd.get('cat_emitida') and not cd.get('numero_cat'):
            self.add_error('numero_cat', 'Informe o número da CAT.')
        if tipo == 'ACIDENTE_COM_AFASTAMENTO' and not cd.get('dias_afastamento'):
            self.add_error('dias_afastamento', 'Informe os dias de afastamento para este tipo de acidente.')

        # Minimização (LGPD art. 6º, III): incidente não guarda dados de saúde
        if not is_acidente:
            cd['funcionario_envolvido'] = None
            cd['parte_corpo_atingida'] = ''
            cd['dias_afastamento'] = 0
            cd['cat_emitida'] = False
            cd['numero_cat'] = ''
        return cd


class InspecaoForm(FilialFormMixin, forms.ModelForm):
    class Meta:
        model = Inspecao
        fields = ['equipamento', 'entrega_epi', 'data_agendada', 'responsavel', 'observacoes']
        widgets = {
            'equipamento': forms.Select(attrs={'class': 'form-select', 'id': 'id_equipamento'}),
            'entrega_epi': forms.Select(attrs={'class': 'form-select', 'id': 'id_entrega_epi'}),
            'data_agendada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                 'placeholder': 'Alguma observação ou instrução para a inspeção?'}),
        }
        labels = {
            'equipamento': 'Equipamento a ser Inspecionado',
            'entrega_epi': 'Item de EPI Específico (opcional)',
            'data_agendada': 'Data de Agendamento',
            'responsavel': 'Inspetor Responsável',
            'observacoes': 'Observações (Opcional)',
        }

    def __init__(self, *args, **kwargs):
        self._pop_filial(kwargs)
        super().__init__(*args, **kwargs)
        f = self.filial

        self.fields['responsavel'].queryset = (
            UserModel.objects.filter(filial_ativa=f, is_active=True).order_by('first_name')
            if f else UserModel.objects.none()
        )
        self.fields['equipamento'].queryset = (
            Equipamento.objects.filter(filial=f, ativo=True).order_by('nome')
            if f else Equipamento.objects.none()
        )
        self.fields['entrega_epi'].required = False
        self.fields['entrega_epi'].queryset = self._entregas_qs(f)

    def _entregas_qs(self, filial):
        if not filial:
            return EntregaEPI.objects.none()
        equip_id = self.data.get('equipamento') if self.data else None
        if not equip_id and self.instance.pk:
            equip_id = self.instance.equipamento_id
        try:
            equip_id = int(equip_id)
        except (TypeError, ValueError):
            return EntregaEPI.objects.none()
        return EntregaEPI.objects.filter(
            filial=filial, equipamento_id=equip_id, data_devolucao__isnull=True,
        ).select_related('ficha__funcionario')

    def clean(self):
        cd = super().clean()
        if not cd.get('equipamento') and not cd.get('entrega_epi'):
            raise forms.ValidationError(
                "A inspeção deve estar ligada a um 'Equipamento' ou a um 'Item de EPI Específico'."
            )
        return cd


class InspecaoConclusaoForm(forms.ModelForm):
    """Conclusão: o técnico NÃO pode trocar equipamento/responsável/status."""

    class Meta:
        model = Inspecao
        fields = ['data_realizacao', 'observacoes']
        widgets = {
            'data_realizacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_data_realizacao(self):
        data = self.cleaned_data.get('data_realizacao') or timezone.localdate()
        if data > timezone.localdate():
            raise forms.ValidationError('A data de realização não pode estar no futuro.')
        return data


class CartaoTagForm(FilialFormMixin, forms.ModelForm):
    class Meta:
        model = CartaoTag
        fields = ['funcionario', 'cargo', 'fone', 'data_validade', 'ativo']
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'fone': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 20}),
            'data_validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self._pop_filial(kwargs)
        super().__init__(*args, **kwargs)
        f = self.filial
        self.fields['funcionario'].queryset = (
            Funcionario.objects.filter(filial=f).only('id', 'nome_completo').order_by('nome_completo')
            if f else Funcionario.objects.none()
        )
        self.fields['cargo'].queryset = (
            Cargo.objects.filter(filial=f).order_by('nome') if f else Cargo.objects.none()
        )


class TipoRiscoForm(FilialFormMixin, forms.ModelForm):
    class Meta:
        model = TipoRisco
        fields = ['categoria', 'nome', 'descricao', 'codigo_cor', 'nr_referencia', 'ativo']
        labels = {
            'categoria': 'Categoria do Risco',
            'nome': 'Nome do Risco / Agente',
            'codigo_cor': 'Cor Identificadora',
            'nr_referencia': 'NR de Referência',
        }
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select', 'id': 'id_categoria'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Ruído, Poeira, Vírus, etc.'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'codigo_cor': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color',
                                                 'style': 'width: 80px; height: 40px; padding: 2px;'}),
            'nr_referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: NR-15, NR-17'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self._pop_filial(kwargs)
        super().__init__(*args, **kwargs)

    def clean(self):
        cd = super().clean()
        categoria, nome = cd.get('categoria'), (cd.get('nome') or '').strip()
        if categoria and nome and self.filial:
            qs = TipoRisco.objects.filter(categoria=categoria, nome__iexact=nome, filial=self.filial)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                label = dict(CATEGORIA_RISCO_CHOICES).get(categoria, categoria)
                raise forms.ValidationError(f'Já existe o risco "{nome}" na categoria "{label}" para esta filial.')
        cd['nome'] = nome
        return cd

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.filial and not instance.filial_id:
            instance.filial = self.filial
        if commit:
            instance.save()
        return instance

