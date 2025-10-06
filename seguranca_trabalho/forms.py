# seguranca_trabalho/forms.py
# seguranca_trabalho/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
import pathlib

# Importa apenas os modelos que realmente existem e são usados nos formulários desta app
from .models import Equipamento, FichaEPI, EntregaEPI, Funcao
from departamento_pessoal.models import Funcionario

# NOTA: FabricanteForm e FornecedorForm foram REMOVIDOS pois seus modelos não existem mais.
# A gestão de Parceiros deve ser feita através de formulários na aplicação 'suprimentos'.


class EquipamentoForm(forms.ModelForm):
    class Meta:
        model = Equipamento
        # REMOVIDO: 'fornecedor' foi retirado da lista de campos.
        fields = [
            'nome', 'modelo', 'fabricante',
            'certificado_aprovacao', 'data_validade_ca', 'vida_util_dias',
            'estoque_minimo', 'requer_numero_serie', 'foto', 'observacoes', 'ativo',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Protetor Auricular Plug'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1100'}),
            # O campo 'fabricante' agora aponta para 'Parceiro', o widget pode ser mantido
            # ou trocado por um de autocomplete na view, se preferir.
            'fabricante': forms.Select(attrs={'class': 'form-select'}),
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

        # Lógica para tornar campos somente leitura na edição (mantida)
        if self.instance.pk:
            self.fields['certificado_aprovacao'].widget.attrs['readonly'] = True
            self.fields['data_validade_ca'].widget.attrs['readonly'] = True
            self.fields['data_validade_ca'].widget = forms.TextInput(
                attrs={'class': 'form-control-plaintext', 'readonly': True}
            )
            if self.instance.data_validade_ca:
                self.initial['data_validade_ca'] = self.instance.data_validade_ca.strftime('%d/%m/%Y')


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
    """ Formulário para o processo de assinatura, atualizando a instância de EntregaEPI. """
    class Meta:
        model = EntregaEPI
        fields = ['assinatura_recebimento', 'assinatura_imagem', 'data_assinatura']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Oculta os campos, pois seus valores são preenchidos via JavaScript.
        self.fields['assinatura_recebimento'].widget = forms.HiddenInput()
        self.fields['assinatura_imagem'].widget = forms.HiddenInput()
        self.fields['data_assinatura'].widget = forms.HiddenInput()

class FuncaoForm(forms.ModelForm):
    class Meta:
        model = Funcao
        # Vamos incluir apenas os campos que o usuário deve preencher.
        # A 'filial' será adicionada automaticamente na view.
        fields = ['nome', 'ativo', 'descricao', 'filial']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'filial': forms.Select(attrs={'class': 'form-select'}),

        }


       