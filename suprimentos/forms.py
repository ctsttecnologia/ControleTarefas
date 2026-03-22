
# suprimentos/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from tributacao.models import NCM, GrupoTributario

from .models import (
    Parceiro, Material, Contrato, VerbaContrato,
    Pedido, ItemPedido, EstoqueConsumo,
    CategoriaMaterial, TipoMaterial,
)


# ═══════════════════════════════════════════════════
# PARCEIRO (preservado)
# ═══════════════════════════════════════════════════
class ParceiroForm(forms.ModelForm):
    class Meta:
        model = Parceiro
        fields = [
            'nome_fantasia', 'razao_social', 'cnpj', 'inscricao_estadual',
            'endereco', 'email', 'telefone', 'celular', 'contato', 'site',
            'observacoes', 'eh_fabricante', 'eh_fornecedor', 'ativo', 'filial',
        ]
        widgets = {
            'filial': forms.Select(attrs={'class': 'form-select'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Fantasia ou Nome do Fabricante'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 0000-0000'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'contato': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pessoa de contato'}),
            'site': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.exemplo.com'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'eh_fabricante': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'eh_fornecedor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UploadFileForm(forms.Form):
    file = forms.FileField(
        label=_("Selecione a planilha (.xlsx)"),
        help_text=_("Apenas arquivos no formato .xlsx são aceitos."),
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file and not file.name.endswith('.xlsx'):
            raise ValidationError(_("Arquivo inválido. Por favor, envie uma planilha no formato .xlsx."))
        return file


# ═══════════════════════════════════════════════════
# MATERIAL (com criação automática de EPI e Ferramenta)
# ═══════════════════════════════════════════════════
class MaterialForm(forms.ModelForm):

    # ── Campos extras: Criar Equipamento EPI (SST) ──
    criar_equipamento_epi = forms.BooleanField(
        required=False,
        label="Criar Equipamento no SST automaticamente",
        help_text="Marque para criar o Equipamento de EPI no módulo de Segurança do Trabalho.",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_criar_equipamento_epi',
        }),
    )
    epi_fabricante = forms.ModelChoiceField(
        queryset=Parceiro.objects.filter(eh_fabricante=True, ativo=True),
        required=False,
        label="Fabricante",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_epi_fabricante',
        }),
    )
    epi_modelo = forms.CharField(
        max_length=100,
        required=False,
        label="Modelo",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Steel Pro Lente',
            'id': 'id_epi_modelo',
        }),
    )
    epi_ca = forms.CharField(
        max_length=50,
        required=False,
        label="Certificado de Aprovação (CA)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 20716',
            'id': 'id_epi_ca',
        }),
    )
    epi_vida_util_dias = forms.IntegerField(
        required=False,
        label="Vida Útil (dias)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'placeholder': 'Ex: 365',
            'id': 'id_epi_vida_util_dias',
        }),
    )

    # ── Campos extras: Criar Ferramenta (ferramentas) ──
    criar_ferramenta = forms.BooleanField(
        required=False,
        label="Criar Ferramenta no módulo de Ferramentas automaticamente",
        help_text="Marque para criar o registro de Ferramenta com controle de movimentação e QR Code.",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_criar_ferramenta',
        }),
    )
    ferr_codigo = forms.CharField(
        max_length=50,
        required=False,
        label="Código de Identificação",
        help_text="Código único da ferramenta (Série/Patrimônio). Gerado automaticamente se vazio.",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: CHAVE-GRIFO-001',
            'id': 'id_ferr_codigo',
        }),
    )
    ferr_patrimonio = forms.CharField(
        max_length=50,
        required=False,
        label="Nº de Patrimônio",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: PAT-00452',
            'id': 'id_ferr_patrimonio',
        }),
    )
    ferr_localizacao = forms.CharField(
        max_length=100,
        required=False,
        label="Localização Padrão",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Almoxarifado, Armário A, Gaveta 3',
            'id': 'id_ferr_localizacao',
        }),
    )
    ferr_data_aquisicao = forms.DateField(
        required=False,
        label="Data de Aquisição",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'id_ferr_data_aquisicao',
        }),
    )
    ferr_fornecedor = forms.ModelChoiceField(
        queryset=Parceiro.objects.filter(eh_fornecedor=True, ativo=True),
        required=False,
        label="Fornecedor",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_ferr_fornecedor',
        }),
    )
    ferr_quantidade = forms.IntegerField(
        required=False,
        label="Quantidade Inicial",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'value': '0',
            'id': 'id_ferr_quantidade',
        }),
    )

    # ═══ NOVO: Campos de Tributação ═══
    ncm = forms.ModelChoiceField(
        queryset=NCM.objects.filter(ativo=True),
        required=False,
        empty_label="— Selecione o NCM —",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Classificação fiscal do material",
    )
    grupo_tributario = forms.ModelChoiceField(
        queryset=GrupoTributario.objects.filter(ativo=True),
        required=False,
        empty_label="— Selecione o Grupo Tributário —",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Perfil fiscal para cálculo de impostos na compra",
    )

    class Meta:
        model = Material
        fields = [
            'descricao', 'classificacao', 'tipo', 'marca',
            'unidade', 'valor_unitario',
            'equipamento_epi', 'ferramenta_ref',
            'ativo', 'ncm', 'grupo_tributario', 'criar_equipamento_epi',
            'epi_fabricante', 'epi_modelo', 'epi_ca', 'epi_vida_util_dias',
            'criar_ferramenta', 'ferr_codigo', 'ferr_patrimonio',
            'ferr_localizacao', 'ferr_data_aquisicao', 'ferr_fornecedor',
        ]
        widgets = {
            'descricao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Fita Isolante 3M Scotch 33+',
            }),
            'classificacao': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_classificacao',
            }),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 3M, GEDORE, MAVARO',
            }),
            'unidade': forms.Select(attrs={'class': 'form-select'}),
            'valor_unitario': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
            }),
            'equipamento_epi': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_equipamento_epi',
            }),
            'ferramenta_ref': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_ferramenta_ref',
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Labels mais claros
        self.fields['equipamento_epi'].label = "🛡️ Vincular ao Equipamento (SST)"
        self.fields['equipamento_epi'].help_text = (
            "Apenas para EPI. Ao receber pedido, dá entrada automática no estoque de SST."
        )
        self.fields['ferramenta_ref'].label = "🔧 Vincular à Ferramenta"
        self.fields['ferramenta_ref'].help_text = (
            "Apenas para Ferramenta. Ao receber pedido, incrementa a quantidade."
        )

        # Campos não obrigatórios
        self.fields['equipamento_epi'].required = False
        self.fields['ferramenta_ref'].required = False

        # Se já tem equipamento vinculado, desabilitar checkbox de criar EPI
        if self.instance and self.instance.pk and self.instance.equipamento_epi:
            self.fields['criar_equipamento_epi'].widget.attrs['disabled'] = True
            self.fields['criar_equipamento_epi'].help_text = "Já vinculado a um equipamento."

        # Se já tem ferramenta vinculada, desabilitar checkbox de criar Ferramenta
        if self.instance and self.instance.pk and self.instance.ferramenta_ref:
            self.fields['criar_ferramenta'].widget.attrs['disabled'] = True
            self.fields['criar_ferramenta'].help_text = "Já vinculado a uma ferramenta."

    def clean(self):
        cleaned_data = super().clean()
        classificacao = cleaned_data.get('classificacao')
        equipamento_epi = cleaned_data.get('equipamento_epi')
        ferramenta_ref = cleaned_data.get('ferramenta_ref')
        criar_epi = cleaned_data.get('criar_equipamento_epi')
        criar_ferr = cleaned_data.get('criar_ferramenta')

        # ── Validação cruzada: classificação × vínculo ──
        if classificacao == CategoriaMaterial.EPI and ferramenta_ref:
            self.add_error(
                'ferramenta_ref',
                'Material EPI não deve ser vinculado a uma Ferramenta.'
            )

        if classificacao == CategoriaMaterial.FERRAMENTA and equipamento_epi:
            self.add_error(
                'equipamento_epi',
                'Material Ferramenta não deve ser vinculado a um Equipamento EPI.'
            )

        if classificacao == CategoriaMaterial.CONSUMO:
            if equipamento_epi:
                self.add_error(
                    'equipamento_epi',
                    'Material de Consumo usa estoque próprio. Não vincule a Equipamento.'
                )
            if ferramenta_ref:
                self.add_error(
                    'ferramenta_ref',
                    'Material de Consumo usa estoque próprio. Não vincule a Ferramenta.'
                )

        # ── Validação: Criar Equipamento EPI ──
        if criar_epi:
            if classificacao != CategoriaMaterial.EPI:
                self.add_error(
                    'criar_equipamento_epi',
                    'Criação automática de equipamento só funciona para materiais EPI.'
                )
            if equipamento_epi:
                self.add_error(
                    'criar_equipamento_epi',
                    'Não marque esta opção se já selecionou um equipamento existente.'
                )
            if not cleaned_data.get('epi_fabricante'):
                self.add_error('epi_fabricante', 'Informe o fabricante para criar o equipamento.')
            if not cleaned_data.get('epi_ca'):
                self.add_error('epi_ca', 'Informe o CA para criar o equipamento.')
            if not cleaned_data.get('epi_vida_util_dias'):
                self.add_error('epi_vida_util_dias', 'Informe a vida útil para criar o equipamento.')

        # ── Validação: Criar Ferramenta ──
        if criar_ferr:
            if classificacao != CategoriaMaterial.FERRAMENTA:
                self.add_error(
                    'criar_ferramenta',
                    'Criação automática de ferramenta só funciona para materiais FERRAMENTA.'
                )
            if ferramenta_ref:
                self.add_error(
                    'criar_ferramenta',
                    'Não marque esta opção se já selecionou uma ferramenta existente.'
                )
            if not cleaned_data.get('ferr_localizacao'):
                self.add_error('ferr_localizacao', 'Informe a localização padrão da ferramenta.')
            if not cleaned_data.get('ferr_data_aquisicao'):
                self.add_error('ferr_data_aquisicao', 'Informe a data de aquisição.')

        return cleaned_data


# ═══════════════════════════════════════════════════
# CONTRATO
# ═══════════════════════════════════════════════════
class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ['cm', 'cliente', 'filial', 'ativo']
        widgets = {
            'cm': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Ex: 776',
            }),
            'cliente': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Ex: SERASA QUINIMURAS',
            }),
            'filial': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ═══════════════════════════════════════════════════
# VERBA MENSAL
# ═══════════════════════════════════════════════════
MES_CHOICES = [(i, f'{i:02d}') for i in range(1, 13)]


class VerbaContratoForm(forms.ModelForm):
    class Meta:
        model = VerbaContrato
        fields = ['ano', 'mes', 'verba_epi', 'verba_consumo', 'verba_ferramenta']
        widgets = {
            'ano': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '2024', 'max': '2030',
            }),
            'mes': forms.Select(attrs={'class': 'form-select'}, choices=MES_CHOICES),
            'verba_epi': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
            }),
            'verba_consumo': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
            }),
            'verba_ferramenta': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
            }),
        }


# ═══════════════════════════════════════════════════
# PEDIDO
# ═══════════════════════════════════════════════════
class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['contrato', 'observacao']
        widgets = {
            'contrato': forms.Select(attrs={'class': 'form-select'}),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Observações gerais do pedido...',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Filtra contratos: ativo + da filial do usuário
        qs = Contrato.objects.filter(ativo=True)
        if self.user and not self.user.is_superuser:
            filial_ativa = getattr(self.user, 'filial_ativa', None)
            if filial_ativa:
                qs = qs.filter(filial=filial_ativa)
        self.fields['contrato'].queryset = qs


class ItemPedidoForm(forms.ModelForm):
    class Meta:
        model = ItemPedido
        fields = ['material', 'quantidade', 'valor_unitario', 'observacao']
        widgets = {
            'material': forms.Select(attrs={
                'class': 'form-select select2-material',
            }),
            'quantidade': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '1', 'value': '1',
            }),
            'valor_unitario': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
            }),
            'observacao': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Opcional',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material'].queryset = Material.objects.filter(ativo=True)


class ReprovarPedidoForm(forms.Form):
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'Informe o motivo da reprovação...',
        }),
        label="Motivo da Reprovação",
    )


class ConfirmarRecebimentoForm(forms.Form):
    """Formulário de confirmação de recebimento do pedido."""
    observacao_recebimento = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'Observações sobre o recebimento (opcional)...',
        }),
        label="Observação do Recebimento",
        required=False,
    )
    confirmar = forms.BooleanField(
        label="Confirmo que recebi todos os itens deste pedido",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )


# ═══════════════════════════════════════════════════
# ESTOQUE CONSUMO (Saída manual)
# ═══════════════════════════════════════════════════
class SaidaConsumoForm(forms.Form):
    """Formulário para registrar saída manual de material de consumo."""
    material = forms.ModelChoiceField(
        queryset=Material.objects.filter(
            ativo=True, classificacao=CategoriaMaterial.CONSUMO
        ),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Material",
    )
    quantidade = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': '1',
        }),
        label="Quantidade",
    )
    justificativa = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Entregue para limpeza do bloco A',
        }),
        label="Justificativa",
    )

