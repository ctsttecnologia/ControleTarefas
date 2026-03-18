# seguranca_trabalho/forms.py


from django import forms
from django.utils.translation import gettext_lazy as _
import pathlib
from .models import Equipamento, FichaEPI, EntregaEPI, Funcao, CargoFuncao
from departamento_pessoal.models import Funcionario
from suprimentos.models import Parceiro
from django_select2.forms import ModelSelect2Widget



class EquipamentoForm(forms.ModelForm):
    estoque_inicial = forms.IntegerField(
        required=False,
        min_value=0,
        label=_("Estoque Atual"),
        help_text=_("Quantidade inicial em estoque. Será registrada como entrada de inventário."),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': '0'}),
    )

    class Meta:
        model = Equipamento
        fields = [
            'nome', 'modelo', 'fabricante',
            'certificado_aprovacao', 'data_validade_ca', 'vida_util_dias',
            'estoque_minimo', 'requer_numero_serie', 'foto', 'observacoes', 'ativo',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Protetor Auricular Plug'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1100'}),
            'fabricante': ModelSelect2Widget(
                model=Parceiro,
                search_fields=['nome_fantasia__icontains', 'razao_social__icontains'],
                attrs={
                    'class': 'form-control',
                    'data-placeholder': 'Buscar fabricante...'
                }
            ),
            'certificado_aprovacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 5745'}),
            'data_validade_ca': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'vida_util_dias': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'estoque_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'requer_numero_serie': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fabricante'].queryset = Parceiro.objects.filter(eh_fabricante=True)

        if self.instance.pk:
            # Edição: campos CA readonly
            self.fields['certificado_aprovacao'].widget.attrs['readonly'] = True
            self.fields['data_validade_ca'].widget = forms.TextInput(
                attrs={'class': 'form-control-plaintext', 'readonly': True}
            )
            if self.instance.data_validade_ca:
                self.initial['data_validade_ca'] = self.instance.data_validade_ca.strftime('%d/%m/%Y')

            # Estoque: readonly na edição, mostra valor atual
            self.fields['estoque_inicial'].label = _("Estoque Atual")
            self.fields['estoque_inicial'].initial = self.instance.estoque_atual
            self.fields['estoque_inicial'].help_text = _(
                "Atualizado automaticamente. Use 'Ajuste de Estoque' para alterar."
            )
            self.fields['estoque_inicial'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control bg-light fw-bold',
                'tabindex': '-1',
            })
        else:
            # Criação: campo editável
            self.fields['estoque_inicial'].label = _("Estoque Inicial")
            self.fields['estoque_inicial'].help_text = _(
                "Quantidade em estoque. Será registrada como entrada de inventário."
            )


class FichaEPIForm(forms.ModelForm):
    class Meta:
        model = FichaEPI
        fields = ['funcionario']
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Filtra funcionários pela filial ativa do usuário logado (lógica mantida)
        if request:
            filial_id = request.session.get('active_filial_id')
            if filial_id:
                self.fields['funcionario'].queryset = Funcionario.objects.filter(
                    filial_id=filial_id, status='ATIVO'
                ).order_by('nome_completo')

    def clean_funcionario(self):
        funcionario = self.cleaned_data.get('funcionario')
        if funcionario and (not hasattr(funcionario, 'cargo') or not funcionario.cargo):
            raise forms.ValidationError(
                _("O funcionário selecionado não possui um cargo definido. Por favor, atualize o cadastro no Departamento Pessoal."),
                code='sem_cargo'
            )
        return funcionario


class EntregaEPIForm(forms.ModelForm):
    class Meta:
        model = EntregaEPI
        fields = ['equipamento', 'quantidade', 'lote', 'numero_serie']
        widgets = {
            'equipamento': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'lote': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        filial = kwargs.pop('filial', None)
        super().__init__(*args, **kwargs)

        # Filtra equipamentos pela filial (lógica mantida)
        queryset = Equipamento.objects.filter(ativo=True)
        if filial:
            queryset = queryset.filter(filial=filial)
        self.fields['equipamento'].queryset = queryset


class AssinaturaForm(forms.Form):
    """ Formulário simples para capturar a assinatura em base64 do frontend. """
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput())


class AssinaturaEntregaForm(forms.ModelForm):
    """Formulário para assinatura: aceita canvas (base64) OU upload de imagem."""
    class Meta:
        model = EntregaEPI
        fields = ['assinatura_recebimento', 'assinatura_imagem', 'data_assinatura']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Base64 do signature_pad → hidden
        self.fields['assinatura_recebimento'].widget = forms.HiddenInput()
        self.fields['assinatura_recebimento'].required = False
        # Upload de imagem → mantém FileInput (NÃO usar HiddenInput!)
        self.fields['assinatura_imagem'].required = False
        # Data preenchida pela view
        self.fields['data_assinatura'].widget = forms.HiddenInput()
        self.fields['data_assinatura'].required = False


class AssinaturaTermoForm(forms.ModelForm):
    class Meta:
        model = FichaEPI
        fields = ['assinatura_funcionario']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assinatura_funcionario'].widget = forms.HiddenInput()
        self.fields['assinatura_funcionario'].required = False


class FuncaoForm(forms.ModelForm):
    class Meta:
        model = Funcao
        # Vamos incluir apenas os campos que o usuário deve preencher.
        # A 'filial' será adicionada automaticamente na view.
        fields = ['nome', 'ativo', 'descricao', 'registro']
        widgets = {
            'registro': forms.NumberInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

        }

class CargoFuncaoForm(forms.ModelForm):
    class Meta:
        model = CargoFuncao
        fields = ['cargo', 'funcao']

    def clean(self):
        cleaned_data = super().clean()
        cargo = cleaned_data.get('cargo')
        funcao = cleaned_data.get('funcao')

        if cargo and funcao:
            # Exclui o próprio objeto em caso de edição
            qs = CargoFuncao.objects.filter(cargo=cargo, funcao=funcao)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"A associação entre '{cargo}' e '{funcao}' já existe."
                )

        return cleaned_data

class AjusteEstoqueForm(forms.Form):
    TIPO_CHOICES = [
        ('ENTRADA', _('Entrada (adicionar ao estoque)')),
        ('SAIDA', _('Saída (remover do estoque)')),
    ]

    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        label=_("Tipo de Ajuste"),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    quantidade = forms.IntegerField(
        min_value=1,
        label=_("Quantidade"),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Ex: 10'}),
    )
    justificativa = forms.CharField(
        label=_("Justificativa"),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: Compra NF 12345 / Ajuste de inventário'}),
    )
