
# ferramentas/forms.py

from django import forms
from django.db import transaction

from .models import (
    Ferramenta, Movimentacao, MalaFerramentas,
    TermoDeResponsabilidade, ItemTermo
)


# =============================================================================
# FORMULÁRIOS DE ITENS
# =============================================================================

class FerramentaForm(forms.ModelForm):
    """
    Formulário para criar/editar Ferramentas.
    Recebe 'request' via kwargs para filtrar querysets por filial.
    """

    class Meta:
        model = Ferramenta
        fields = [
            'nome', 'codigo_identificacao', 'data_aquisicao',
            'localizacao_padrao', 'patrimonio', 'fabricante_marca',
            'modelo', 'serie', 'tamanho_polegadas',
            'numero_laudo_tecnico', 'fornecedor', 'mala',
            'observacoes', 'quantidade',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Furadeira de Impacto'}),
            'patrimonio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nº de patrimônio'}),
            'codigo_identificacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: PAT-001-FURADEIRA'}),
            'fabricante_marca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bosch'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: PL56843'}),
            'serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 56843'}),
            'tamanho_polegadas': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 12'}),
            'numero_laudo_tecnico': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 215231'}),
            'localizacao_padrao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Armário 2, Prateleira A'}),
            'data_aquisicao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'mala': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request:
            from suprimentos.models import Parceiro

            # Filtra malas pela filial ativa
            self.fields['mala'].queryset = (
                MalaFerramentas.objects.for_request(self.request).order_by('nome')
            )

            # Filtra fornecedores pela filial (se Parceiro usa FilialManager)
            # Se Parceiro NÃO tem FilialManager, remova este bloco
            try:
                self.fields['fornecedor'].queryset = (
                    Parceiro.objects.for_request(self.request).order_by('razao_social')
                )
            except AttributeError:
                # Parceiro não tem for_request — mantém queryset padrão
                pass

        # Desabilita campos na edição
        if self.instance and self.instance.pk:
            self.fields['data_aquisicao'].disabled = True
            self.fields['mala'].disabled = True

    def clean_codigo_identificacao(self):
        return self.cleaned_data['codigo_identificacao'].upper().strip()


class MalaFerramentasForm(forms.ModelForm):
    """
    Formulário para criar/editar Malas com seleção de ferramentas.
    Recebe 'request' para filtrar ferramentas pela filial ativa.
    """

    itens = forms.ModelMultipleChoiceField(
        queryset=Ferramenta.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Ferramentas na Mala"
    )

    class Meta:
        model = MalaFerramentas
        fields = ['nome', 'codigo_identificacao', 'localizacao_padrao']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Kit de Manutenção Elétrica'}),
            'codigo_identificacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MALA-ELETR-01'}),
            'localizacao_padrao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Local de guarda'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        mala_pk = self.instance.pk if self.instance else None

        # Base: ferramentas disponíveis para mala
        qs = Ferramenta.objects.ferramentas_disponiveis_para_mala(mala_instance_pk=mala_pk)

        # Filtra pela filial ativa do request
        if self.request:
            qs = qs.for_request(self.request)

        self.fields['itens'].queryset = qs.order_by('nome')

        if self.instance and self.instance.pk:
            self.fields['itens'].initial = self.instance.itens.all()

    def clean_codigo_identificacao(self):
        return self.cleaned_data['codigo_identificacao'].upper().strip()

    @transaction.atomic
    def save(self, commit=True):
        mala = super().save(commit=True)
        ferramentas_selecionadas = set(self.cleaned_data['itens'])
        ferramentas_atuais = set(mala.itens.all())

        # Remove ferramentas desmarcadas
        for f in ferramentas_atuais - ferramentas_selecionadas:
            f.mala = None
            f.save(update_fields=['mala'])

        # Adiciona novas ferramentas
        for f in ferramentas_selecionadas - ferramentas_atuais:
            f.mala = mala
            f.save(update_fields=['mala'])

        # Atualiza contagem
        mala.quantidade = len(ferramentas_selecionadas)
        mala.save(update_fields=['quantidade'])

        return mala


# =============================================================================
# FORMULÁRIOS DE MOVIMENTAÇÃO
# =============================================================================

class MovimentacaoForm(forms.ModelForm):
    """
    Formulário de retirada (Movimentação).
    O campo 'retirado_por' é filtrado por usuários da filial ativa.
    """
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput(), required=True)

    class Meta:
        model = Movimentacao
        fields = ['retirado_por', 'data_devolucao_prevista', 'condicoes_retirada']
        widgets = {
            'retirado_por': forms.Select(attrs={'class': 'form-select'}),
            'data_devolucao_prevista': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'condicoes_retirada': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Descreva o estado do item (arranhões, funcionamento, etc.)'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.ferramenta = kwargs.pop('ferramenta', None)
        self.mala = kwargs.pop('mala', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Filtra usuários pela filial ativa
        if self.request:
            from usuario.models import Usuario

            filial_ativa = self.request.user.filial_ativa
            if filial_ativa:
                self.fields['retirado_por'].queryset = (
                    Usuario.objects.filter(
                        filiais_permitidas=filial_ativa,
                        is_active=True
                    ).order_by('first_name', 'last_name')
                )

    def clean(self):
        cleaned_data = super().clean()
        if not self.ferramenta and not self.mala:
            raise forms.ValidationError("Movimentação sem item associado.")
        if self.ferramenta and self.mala:
            raise forms.ValidationError(
                "Movimentação não pode ser de ferramenta e mala simultaneamente."
            )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.ferramenta:
            instance.ferramenta = self.ferramenta
        if self.mala:
            instance.mala = self.mala
        if commit:
            instance.save()
        return instance


class DevolucaoForm(forms.ModelForm):
    """Formulário de devolução de ferramenta/mala."""
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Movimentacao
        fields = ['condicoes_devolucao']
        widgets = {
            'condicoes_devolucao': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Descreva como o item foi devolvido. Aponte qualquer dano ou problema.'
            }),
        }


# =============================================================================
# FORMULÁRIOS UTILITÁRIOS
# =============================================================================

class UploadFileForm(forms.Form):
    """Upload de planilha Excel para importação."""
    file = forms.FileField(
        label="Selecione a planilha (.xlsx)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'})
    )

    def clean_file(self):
        f = self.cleaned_data['file']
        if not f.name.endswith('.xlsx'):
            raise forms.ValidationError("Apenas arquivos .xlsx são aceitos.")
        if f.size > 5 * 1024 * 1024:  # 5MB
            raise forms.ValidationError("Arquivo muito grande. Máximo: 5MB.")
        return f


# =============================================================================
# FORMULÁRIO DO TERMO DE RESPONSABILIDADE
# =============================================================================

class TermoResponsabilidadeForm(forms.ModelForm):
    """
    Formulário para criar Termos de Responsabilidade.
    Todos os campos de FK são filtrados pela filial ativa via request.
    """
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput(), required=False)

    ferramentas_selecionadas = forms.ModelMultipleChoiceField(
        queryset=Ferramenta.objects.none(),
        required=False,
        label="Ferramentas"
    )
    malas_selecionadas = forms.ModelMultipleChoiceField(
        queryset=MalaFerramentas.objects.none(),
        required=False,
        label="Malas/Kits"
    )

    class Meta:
        model = TermoDeResponsabilidade
        fields = ['contrato', 'responsavel', 'separado_por', 'data_emissao', 'tipo_uso']
        widgets = {
            'contrato': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Contrato CETEST-2026/001'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'separado_por': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'tipo_uso': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request:
            from departamento_pessoal.models import Funcionario

            # ==========================================================
            # FUNCIONÁRIOS: filtrados pela filial ativa + apenas ativos
            # ==========================================================
            funcionarios_filial = Funcionario.objects.for_request(request).filter(
                status='ATIVO'
            ).order_by('nome_completo')

            self.fields['responsavel'].queryset = funcionarios_filial
            self.fields['separado_por'].queryset = funcionarios_filial

            # ==========================================================
            # FERRAMENTAS E MALAS: filtradas por filial + disponíveis
            # ==========================================================
            self.fields['ferramentas_selecionadas'].queryset = (
                Ferramenta.objects.for_request(request).disponiveis()
            )
            self.fields['malas_selecionadas'].queryset = (
                MalaFerramentas.objects.for_request(request).filter(
                    status=MalaFerramentas.Status.DISPONIVEL
                )
            )

class ItemTermoForm(forms.ModelForm):
    class Meta:
        model = ItemTermo
        fields = ['quantidade', 'unidade', 'item']

