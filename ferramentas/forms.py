# ferramentas/forms.py

from django import forms
from django.db import transaction
from ata_reuniao import models
from .models import Ferramenta, Movimentacao, MalaFerramentas, Usuario, Atividade
from django.db.models import Q

from .models import TermoDeResponsabilidade, ItemTermo


# =============================================================================
# == FORMULÁRIOS DE ITENS (Ferramentas e Malas)
# =============================================================================

class FerramentaForm(forms.ModelForm):
    class Meta:
        model = Ferramenta
        # Removido 'status' para que seja controlado por ações (retirada, manutenção)
        # e não por edição manual. O campo 'mala' é adicionado para contexto.
        fields = [
            'nome', 'id', 'codigo_identificacao', 'data_aquisicao', 'localizacao_padrao', 'patrimonio', 'fabricante_marca', 'modelo',
            'serie', 'tamanho_polegadas', 'numero_laudo_tecnico', 'filial', 'mala', 'observacoes', 'quantidade'
        ]
        
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Furadeira de Impacto'}),
            'patrimonio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nº de patrimônio ou ativo fixo'}),
            'codigo_identificacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código, ex: '
            'Patrimônio-Nome do Equipamento'}),
            'fabricante_marca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bosch, DeWalt'}),
            'modelo ': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: PL56843'}),
            'serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 56843'}),
            'tamanho_polegadas': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 12'}),
            'numero_laudo_tecnico': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 215231'}), 
            'localizacao_padrao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Armário 2, Prateleira A'}),
            'data_aquisicao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_descarte': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'mala': forms.Select(attrs={'class': 'form-select', 'disabled': 'disabled'}), # Aparece desabilitado
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        help_texts = {
            'mala': 'Para alterar a mala de uma ferramenta, edite a mala diretamente.'
        }

        def __init__(self, *args, **kwargs):
                # Primeiro, execute o __init__ da classe pai
                super().__init__(*args, **kwargs)
                
                # Agora, adicione a nossa lógica customizada.
                # 'self.instance' é o objeto que está sendo editado.
                # 'self.instance.pk' só existe se o objeto já foi salvo no banco (ou seja, é uma edição).
                if self.instance and self.instance.pk:
                    # Se estamos editando um objeto existente, desabilite o campo.
                    self.fields['data_aquisicao'].disabled = True


    # Garante que o código seja sempre salvo em maiúsculas para consistência.
    def clean_codigo_identificacao(self):
        return self.cleaned_data['codigo_identificacao'].upper()


# Campo customizado para exibir mais detalhes na seleção de ferramentas
class MalaItemChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        # Exibe "Nome da Ferramenta (COD123)" na lista de checkboxes
        return f"{obj.nome} ({obj.codigo_identificacao})"


class MalaFerramentasForm(forms.ModelForm):

    
    itens = forms.ModelMultipleChoiceField(
        queryset=Ferramenta.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Ferramentas na Mala"
    )
    """
    Formulário para criar e atualizar Malas de Ferramentas.

    Este formulário customiza a lógica para:
    1. Exibir dinamicamente apenas as ferramentas que podem ser adicionadas a uma mala.
    2. Calcular e salvar automaticamente a 'quantidade' com base no número de 
       itens selecionados.
    """
    class Meta:
        model = MalaFerramentas
        fields = ['nome', 'id', 'codigo_identificacao', 'localizacao_padrao', 'quantidade']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Kit de Manutenção Elétrica'}),
            'codigo_identificacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código, ex: MALA-ELETR-01'}),
            'localizacao_padrao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Local onde a mala é guardada'}),
        }
        # O campo 'itens' é declarado explicitamente abaixo, então não precisamos 
        # nos preocupar com o widget aqui.

    def __init__(self, *args, **kwargs):
        """
        Sobrescreve o __init__ para customizar o campo 'itens' dinamicamente.
        """
        super().__init__(*args, **kwargs)
        
        # Determina o queryset base para as ferramentas disponíveis.
        # Ao criar uma nova mala, pegamos todas as ferramentas que não estão em nenhuma mala.
        # Ao editar, pegamos as que não estão em nenhuma mala OU as que já estão nesta mala.
        mala_instance_pk = self.instance.pk if self.instance else None
        queryset_ferramentas = Ferramenta.objects.ferramentas_disponiveis_para_mala(
            mala_instance_pk=mala_instance_pk
        )
        
        # Define ou atualiza o campo 'itens' com o queryset dinâmico.
        self.fields['itens'] = forms.ModelMultipleChoiceField(
            queryset=queryset_ferramentas,
            widget=forms.CheckboxSelectMultiple,
            required=False,
            label="Ferramentas na Mala"
        )
        if self.instance and self.instance.pk:
            # Pré-seleciona os itens que já pertencem a esta mala
            self.fields['itens'].initial = self.instance.itens.all()

    def save(self, commit=True):
        # 1. Salva a instância da Mala primeiro, para garantir que ela exista.
        mala_instance = super().save(commit=True)
        
        # 2. Pega a lista de ferramentas que foram SELECIONADAS no formulário.
        ferramentas_selecionadas = self.cleaned_data['itens']
        
        # 3. Pega a lista de ferramentas que ATUALMENTE estão associadas a esta mala.
        ferramentas_atuais = mala_instance.itens.all()
        
        # 4. Remove a associação das ferramentas que foram desmarcadas.
        #    Para cada ferramenta que ESTAVA na mala mas NÃO ESTÁ na nova seleção,
        #    definimos sua 'mala' como None.
        for ferramenta in ferramentas_atuais:
            if ferramenta not in ferramentas_selecionadas:
                ferramenta.mala = None
                ferramenta.save()

        # 5. Adiciona a associação para as novas ferramentas marcadas.
        #    Para cada ferramenta que foi SELECIONADA, definimos sua 'mala'
        #    para ser a instância da mala que estamos salvando.
        for ferramenta in ferramentas_selecionadas:
            if ferramenta.mala != mala_instance:
                ferramenta.mala = mala_instance
                ferramenta.save()

        # 6. Atualiza a contagem de itens na mala.
        mala_instance.quantidade = ferramentas_selecionadas.count()
        mala_instance.save(update_fields=['quantidade'])
            
        return mala_instance


# =============================================================================
# == FORMULÁRIOS DE MOVIMENTAÇÃO (Reutilizáveis para Ferramentas e Malas)
# =============================================================================

class MovimentacaoForm(forms.ModelForm):
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput(), required=True)

    class Meta:
        model = Movimentacao
        fields = ['retirado_por', 'data_devolucao_prevista', 'condicoes_retirada']
        widgets = {
            'retirado_por': forms.Select(attrs={'class': 'form-select'}),
            'data_devolucao_prevista': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'condicoes_retirada': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Captura a ferramenta ou a mala passada pela view
        self.ferramenta = kwargs.pop('ferramenta', None)
        self.mala = kwargs.pop('mala', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        # Pega os dados já validados dos campos individuais
        cleaned_data = super().clean()

        # Agora, a validação usa self.ferramenta e self.mala, que foram definidos no __init__
        if not self.ferramenta and not self.mala:
            raise forms.ValidationError(
                "A movimentação não está associada a nenhum item. Contate o administrador do sistema."
            )
        
        if self.ferramenta and self.mala:
            raise forms.ValidationError(
                "Erro do sistema: A movimentação não pode ser de uma ferramenta e uma mala ao mesmo tempo."
            )
            
        return cleaned_data

    def save(self, commit=True):
        # Associa a ferramenta ou a mala antes de salvar
        instance = super().save(commit=False)
        if self.ferramenta:
            instance.ferramenta = self.ferramenta
        if self.mala:
            instance.mala = self.mala
        
        if commit:
            instance.save()
        return instance


class DevolucaoForm(forms.ModelForm):
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput(), required=True)
    
    class Meta:
        model = Movimentacao
        fields = ['condicoes_devolucao']
        
        widgets = {
            'condicoes_devolucao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descreva como o item foi devolvido. Aponte qualquer dano ou problema.'}),
        }

# =============================================================================
# == FORMULÁRIOS UTILITÁRIOS
# =============================================================================

class UploadFileForm(forms.Form):
    """ Formulário simples para o upload de um arquivo de planilha. """
    file = forms.FileField(
        label="Selecione a planilha (.xlsx)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'})
    )


# Form termos de responsabilidade

class TermoResponsabilidadeForm(forms.ModelForm):
    
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput(), required=False)
        
   # Campos para selecionar itens. Transformados em caixas de pesquisa pelo Select2.

    ferramentas_selecionadas = forms.ModelMultipleChoiceField(
        queryset=Ferramenta.objects.filter(status=Ferramenta.Status.DISPONIVEL),
        required=False,
        label="Ferramentas"
    )
    malas_selecionadas = forms.ModelMultipleChoiceField(
        queryset=MalaFerramentas.objects.filter(status=MalaFerramentas.Status.DISPONIVEL),
        required=False,
        label="Malas/Kits"
    )
    
    assinatura_base64 = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = TermoDeResponsabilidade
        fields = ['contrato', 'responsavel', 'separado_por', 'data_emissao', 'tipo_uso']
        widgets = {
            'data_emissao': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d' # Garante o formato correto para o input date
            ),
        }
    def __init__(self, *args, **kwargs):
        # Filtra os QuerySets para a filial do usuário que está fazendo a requisição
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if request:
            # Garante que apenas itens da filial do usuário sejam exibidos para seleção
            self.fields['ferramentas_selecionadas'].queryset = Ferramenta.objects.for_request(request).filter(status=Ferramenta.Status.DISPONIVEL)
            self.fields['malas_selecionadas'].queryset = MalaFerramentas.objects.for_request(request).filter(status=MalaFerramentas.Status.DISPONIVEL)

# Este formulário é apenas para a lógica, a submissão será feita no TermoResponsabilidadeForm
class ItemTermoForm(forms.ModelForm):
    class Meta:
        model = ItemTermo
        fields = ['quantidade', 'unidade', 'item']


