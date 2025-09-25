# ferramentas/forms.py

from django import forms
from django.db import transaction
from ata_reuniao import models
from .models import Ferramenta, Movimentacao, MalaFerramentas, Usuario, Atividade
from django.db.models import Q



# =============================================================================
# == FORMULÁRIOS DE ITENS (Ferramentas e Malas)
# =============================================================================

class FerramentaForm(forms.ModelForm):
    class Meta:
        model = Ferramenta
        # Removido 'status' para que seja controlado por ações (retirada, manutenção)
        # e não por edição manual. O campo 'mala' é adicionado para contexto.
        fields = [
            'nome', 'codigo_identificacao', 'data_aquisicao', 'localizacao_padrao', 'patrimonio', 'fabricante_marca', 'modelo',
            'serie', 'tamanho_polegadas', 'numero_laudo_tecnico', 'filial', 'mala', 'observacoes'
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

    class Meta:
        model = MalaFerramentas
        fields = ['nome', 'codigo_identificacao', 'localizacao_padrao', 'itens']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Kit de Manutenção Elétrica'}),
            'codigo_identificacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código, ex: MALA-ELETR-01'}),
            'localizacao_padrao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Local onde a mala é guardada'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # O queryset inicial para o campo "itens" é a base para o que pode ser selecionado.
        # Ele já exclui ferramentas em uso que não estão nesta mala.
        if self.instance and self.instance.pk:
            # Ao editar: permite ferramentas na própria mala OU disponíveis e sem mala
            self.fields['itens'].queryset = Ferramenta.objects.filter(
                Q(mala__isnull=True, status=Ferramenta.Status.DISPONIVEL) | 
                Q(mala=self.instance)
            ).order_by('nome')
            self.fields['itens'].initial = self.instance.itens.all()
        else:
            # Ao criar: permite apenas ferramentas disponíveis e sem mala
            self.fields['itens'].queryset = Ferramenta.objects.filter(
                mala__isnull=True, status=Ferramenta.Status.DISPONIVEL
            ).order_by('nome')

    def clean_itens(self):
        """
        Valida se as ferramentas selecionadas estão realmente disponíveis para serem adicionadas ou mantidas na mala.
        Esta validação é crucial porque o JavaScript no frontend pode permitir a seleção de itens que não deveriam.
        """
        selected_items = self.cleaned_data['itens']
        
        # Filtra as ferramentas que já estão nesta mala (se estiver editando)
        # ou que estão disponíveis e não em nenhuma mala (se estiver criando).
        # A validação final deve ser feita contra o estado ATUAL do banco de dados.
        
        # Se for uma nova mala ou uma mala existente, verificamos se os itens selecionados
        # não estão 'em uso' fora desta mala ou 'em manutenção'.
        
        # Obter os IDs dos itens que *realmente* estão em uso ou em manutenção.
        # Excluímos da verificação os itens que já pertencem a esta mala (se houver).
        
        # Itens que o usuário tentou adicionar/manter
        pks_selecionados = [f.pk for f in selected_items]
        
        # Se estiver editando uma mala, os itens que já estão nela são permitidos.
        # Precisamos verificar se os *novos* itens ou os itens que já estavam e foram mantidos
        # não estão em status incompatível.
        
        # Ferramentas que não estão em nenhuma mala OU que estão nesta mala E estão 'Disponíveis'
        # Esta é a base do que é *permitido* ser vinculado.
        allowed_items_qs = Ferramenta.objects.filter(
            Q(mala__isnull=True, status=Ferramenta.Status.DISPONIVEL) | 
            Q(mala=self.instance) # Se estiver editando, os itens atuais da mala são permitidos
        )
        allowed_pks = list(allowed_items_qs.values_list('pk', flat=True))

        # Encontra ferramentas selecionadas que NÃO estão na lista de permitidos
        invalid_items = [f for f in selected_items if f.pk not in allowed_pks]
        
        if invalid_items:
            # Coleta os nomes dos itens inválidos para a mensagem de erro
            invalid_names = ", ".join([item.nome for item in invalid_items])
            if self.instance and self.instance.pk:
                raise forms.ValidationError(
                    f"As seguintes ferramentas não podem ser adicionadas/mantidas na mala '{self.instance.nome}' "
                    f"porque estão em uso em outra mala ou em manutenção: {invalid_names}."
                )
            else:
                 raise forms.ValidationError(
                    f"As seguintes ferramentas não podem ser adicionadas à nova mala "
                    f"porque estão em uso em outra mala ou em manutenção: {invalid_names}."
                )
        
        return selected_items

    @transaction.atomic
    def save(self, commit=True):
        mala_instance = super().save(commit=False)
        
        if commit:
            mala_instance.save()

        ferramentas_selecionadas = self.cleaned_data['itens']
        pks_selecionados = list(ferramentas_selecionadas.values_list('pk', flat=True))

        # Desvincula APENAS as ferramentas que pertenciam a esta mala e NÃO foram mais selecionadas.
        # As ferramentas que já estavam e foram mantidas não precisam ser desvinculadas e revinculadas.
        # Isso otimiza a operação e ajuda a evitar o erro 1093 em alguns contextos,
        # embora o problema principal era a subquery no UPDATE.
        Ferramenta.objects.filter(mala=mala_instance).exclude(pk__in=pks_selecionados).update(mala=None)

        # Vincula APENAS as ferramentas selecionadas que AINDA NÃO estão nesta mala.
        # Isso garante que apenas as ferramentas novas ou as que foram removidas e adicionadas de novo sejam atualizadas.
        Ferramenta.objects.filter(pk__in=pks_selecionados).exclude(mala=mala_instance).update(mala=mala_instance)
        
        if commit:
            self.save_m2m() # Manter se houver outras relações ManyToMany

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



