
"""
Formulários para o módulo
"""
from django import forms
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from dal import autocomplete
from cliente.models import Cliente
from departamento_pessoal.models import Cargo
from seguranca_trabalho.models import Funcao

from .models import (
    AcompanhamentoPlanoAcao,
    AmbienteTrabalho,
    PGRDocumento, 
    Empresa, 
    LocalPrestacaoServico,
    ProfissionalResponsavel,
    PGRDocumentoResponsavel, 
    GESGrupoExposicao,
    RiscoIdentificado,
    PlanoAcaoPGR,
    CronogramaAcaoPGR,
    PGRRevisao,
    AvaliacaoQuantitativa,
    #MedidaControleRisco
)


# ========================================
# FORMULÁRIO DE EMPRESA
# ========================================

class EmpresaForm(forms.ModelForm):
    """Formulário para cadastro de empresas"""
    
    class Meta:
        model = Empresa
        fields = [
            'cliente', 'cnpj', 'tipo_empresa', 'cnae_especifico', 'descricao_cnae',
            'atividade_principal', 'grau_risco', 'grau_risco_texto',
            'numero_empregados', 'numero_empregados_texto', 'jornada_trabalho',
            'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            'cep', 'telefone', 'ativo'
        ]
        
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '00.000.000/0000-00'}),
            'tipo_empresa': forms.Select(attrs={'class': 'form-select'}),
            'cnae_especifico': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao_cnae': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'atividade_principal': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'grau_risco': forms.Select(attrs={'class': 'form-select'}),
            'grau_risco_texto': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_empregados': forms.NumberInput(attrs={'class': 'form-control'}),
            'numero_empregados_texto': forms.TextInput(attrs={'class': 'form-control'}),
            'jornada_trabalho': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '00000-000'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '(00) 00000-0000'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ========================================
# FORMULÁRIO DE LOCAL DE PRESTAÇÃO
# ========================================

class LocalPrestacaoServicoForm(forms.ModelForm):
    """Formulário para locais de prestação de serviços"""
    
    class Meta:
        model = LocalPrestacaoServico
        fields = [
            'empresa', 'razao_social', 'cnpj', 'descricao',
            'endereco', 'numero', 'bairro', 'cidade', 'estado', 'cep', 'ativo'
        ]
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '00.000.000/0000-00'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '00000-000'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ========================================
# FORMULÁRIO DE PROFISSIONAL RESPONSÁVEL
# ========================================

class ProfissionalResponsavelForm(forms.ModelForm):
    """Formulário para profissionais responsáveis"""
    
    class Meta:
        model = ProfissionalResponsavel
        fields = [
            'nome_completo', 'funcao', 'registro_classe', 'orgao_classe',
            'especialidade', 'telefone', 'email', 'ativo'
        ]
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'funcao': forms.TextInput(attrs={'class': 'form-control'}),
            'registro_classe': forms.TextInput(attrs={'class': 'form-control'}),
            'orgao_classe': forms.TextInput(attrs={'class': 'form-control'}),
            'especialidade': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

ResponsavelFormSet = forms.inlineformset_factory(
    PGRDocumento,  # Modelo Pai
    PGRDocumentoResponsavel,  # Modelo Filho (o vínculo)
    fields=('profissional', 'tipo_responsabilidade'),  # Campos a serem exibidos no formulário
    extra=1,  # Começar com 1 formulário em branco para adicionar um novo
    can_delete=True,  # Permitir que os usuários marquem itens para exclusão
    widgets={
        'profissional': forms.Select(attrs={'class': 'form-control'}),
        'tipo_responsabilidade': forms.Select(attrs={'class': 'form-control'}),
    }
)

# ========================================
# FORMULÁRIO DE DOCUMENTO PGR
# ========================================

class PGRDocumentoForm(forms.ModelForm):
    """Formulário para documento PGR"""
    
    def __init__(self, *args, **kwargs):
        # Remove 'user' dos kwargs para não passar para o super().__init__
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if request:
            # Chame o manager com o objeto request, como ele espera
            self.fields['empresa'].queryset = Cliente.objects.for_request(request)

    class Meta:
        model = PGRDocumento
        fields = [
            'codigo_documento', 'empresa', 'local_prestacao',
            'data_elaboracao', 'data_vencimento', 'data_ultima_revisao',
            'versao_atual', 'status', 'observacoes', 'objetivo', 'escopo', 'metodologia_avaliacao',
        ]
        widgets = {
            'codigo_documento': forms.TextInput(attrs={'class': 'form-control'}),
            # Agora você pode usar o autocomplete OU o Select, mas o queryset já está filtrado!
            #'empresa': forms.Select(attrs={'class': 'form-select'}),  
            'empresa': autocomplete.ModelSelect2(
                url='pgr_gestao:cliente-autocomplete',
                attrs={
                    'data-placeholder': 'Digite o nome da empresa...',
                    'data-minimum-input-length': 1,
                    'class': 'form-select', 
                }
            ),
            'local_prestacao': forms.Select(attrs={'class': 'form-select'}),
            'data_elaboracao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_ultima_revisao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'versao_atual': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'objetivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'escopo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'metodologia_avaliacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        
        # Usamos .pop() para pegar o valor e ao mesmo tempo tirá-lo do dicionário.
        request = kwargs.pop('request', None)
        
        #Chame o __init__ da classe pai, agora SEM o 'request' nos kwargs.
        super().__init__(*args, **kwargs)

        # Verificamos se o formulário está sendo usado para editar um objeto existente
        # (se a instância já tem uma chave primária/pk)
        if self.instance and self.instance.pk:
            # Se for uma edição, desabilita o campo 'data_elaboracao'
            self.fields['data_elaboracao'].disabled = True
            self.fields['data_vencimento'].disabled = True

            # Define o campo como não-obrigatório para a validação do form
            self.fields['data_elaboracao'].required = False
            self.fields['data_vencimento'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        data_elaboracao = cleaned_data.get('data_elaboracao')
        data_vencimento = cleaned_data.get('data_vencimento')
        
        
        if data_elaboracao and data_vencimento:
            if data_vencimento <= data_elaboracao:
                raise ValidationError('A data de vencimento deve ser posterior à data de elaboração.')
        
        return cleaned_data

# ========================================
# FORMULÁRIO DE GES
# ========================================

class GESForm(forms.ModelForm):
    """Formulário para Grupo de Exposição Similar"""
    
    class Meta:
        model = GESGrupoExposicao
        fields = [
            'pgr_documento', 'codigo', 'nome', 'ambiente_trabalho', 'cargo', 'funcao',
            'numero_trabalhadores', 'descricao_atividades', 'jornada_trabalho',
            'horario_trabalho', 'ativo'
        ]
        widgets = {
            'pgr_documento': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'ambiente_trabalho': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'funcao': forms.Select(attrs={'class': 'form-select'}),
            'numero_trabalhadores': forms.NumberInput(attrs={'class': 'form-control'}),
            'descricao_atividades': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'jornada_trabalho': forms.TextInput(attrs={'class': 'form-control'}),
            'horario_trabalho': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class GESGrupoExposicaoForm(forms.ModelForm):
    """
    Formulário para criar e editar Grupos de Exposição Similar (GES).
    """

    class Meta:
        model = GESGrupoExposicao
        fields = [
            'pgr_documento',
            'codigo',
            'nome',
            'ambiente_trabalho',
            'cargo',
            'funcao',
            'numero_trabalhadores',
            'jornada_trabalho',
            'horario_trabalho',
            'descricao_atividades',
            'equipamentos_utilizados',
            'produtos_manipulados',
            'ativo',  # <-- ADICIONADO
        ]

        widgets = {
            'pgr_documento': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: GES-001'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Administração, Produção Linha A'}),
            'ambiente_trabalho': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'funcao': forms.Select(attrs={'class': 'form-select'}),
            'numero_trabalhadores': forms.NumberInput(attrs={'class': 'form-control'}),
            'jornada_trabalho': forms.TextInput(attrs={'class': 'form-control'}),
            'horario_trabalho': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 08:00 às 17:00'}),
            'descricao_atividades': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'equipamentos_utilizados': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'produtos_manipulados': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

        help_texts = {
            'codigo': 'Código único para identificar o GES dentro do PGR. Deixe em branco para gerar automaticamente.',
            'nome': 'Um nome descritivo para o grupo, como o setor ou a equipe.',
            'ambiente_trabalho': 'Selecione o ambiente onde este grupo trabalha.',
            'cargo': 'Selecione o cargo principal dos trabalhadores neste grupo.',
            'ativo': 'Desmarque para inativar este GES no PGR (não será incluído no relatório PDF).',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(GESGrupoExposicaoForm, self).__init__(*args, **kwargs)

        if user and user.is_authenticated and hasattr(user, 'filial'):
            self.fields['pgr_documento'].queryset = PGRDocumento.objects.filter(filial=user.filial)
            self.fields['ambiente_trabalho'].queryset = AmbienteTrabalho.objects.filter(filial=user.filial)
            self.fields['cargo'].queryset = Cargo.objects.filter(filial=user.filial)
            self.fields['funcao'].queryset = Funcao.objects.filter(filial=user.filial)

        if self.instance and self.instance.pk:
            self.fields['pgr_documento'].disabled = True

    def clean_codigo(self):
        """Garante que o código seja único para o PGR."""
        codigo = self.cleaned_data.get('codigo')
        pgr_documento = self.cleaned_data.get('pgr_documento')

        if codigo:
            queryset = GESGrupoExposicao.objects.filter(
                pgr_documento=pgr_documento,
                codigo__iexact=codigo
            )
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise forms.ValidationError(
                    'Já existe um GES com este código neste Documento PGR.'
                )

        return codigo
    
# ========================================
# FORMULÁRIO DE RISCO IDENTIFICADO
# ========================================

class RiscoIdentificadoForm(forms.ModelForm):
    """Formulário para identificação de riscos"""
    
    class Meta:
        model = RiscoIdentificado
        fields = [
            'pgr_documento', 'ges', 'codigo_risco', 'tipo_risco', 'agente',
            'fonte_geradora', 'meio_propagacao', 'perfil_exposicao',
            'possiveis_efeitos_saude', 'ambiente_trabalho', 'cargo',
            'gravidade_g', 'exposicao_e', 'severidade_s', 'probabilidade_p',
            'classificacao_risco', 'prioridade_acao', 'metodo_avaliacao',
            'status_controle', 'medidas_controle_existentes', 'observacoes',
            'data_identificacao'
        ]
        widgets = {
            'pgr_documento': forms.Select(attrs={'class': 'form-select'}),
            'ges': forms.Select(attrs={'class': 'form-select'}),
            'codigo_risco': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_risco': forms.Select(attrs={'class': 'form-select'}),
            'agente': forms.TextInput(attrs={'class': 'form-control'}),
            'fonte_geradora': forms.TextInput(attrs={'class': 'form-control'}),
            'meio_propagacao': forms.TextInput(attrs={'class': 'form-control'}),
            'perfil_exposicao': forms.Select(attrs={'class': 'form-select'}),
            'possiveis_efeitos_saude': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ambiente_trabalho': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'gravidade_g': forms.Select(attrs={'class': 'form-select'}),
            'exposicao_e': forms.Select(attrs={'class': 'form-select'}),
            'severidade_s': forms.Select(attrs={'class': 'form-select'}),
            'probabilidade_p': forms.Select(attrs={'class': 'form-select'}),
            'classificacao_risco': forms.Select(attrs={'class': 'form-select'}),
            'prioridade_acao': forms.Select(attrs={'class': 'form-select'}),
            'metodo_avaliacao': forms.Select(attrs={'class': 'form-select'}),
            'status_controle': forms.Select(attrs={'class': 'form-select'}),
            'medidas_controle_existentes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'data_identificacao': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d',
            ),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deixar campos calculados como readonly
        self.fields['severidade_s'].widget.attrs['readonly'] = True
        self.fields['classificacao_risco'].widget.attrs['readonly'] = True
        self.fields['prioridade_acao'].widget.attrs['readonly'] = True
        
        # Filtrar GES pelo documento
        if 'pgr_documento' in self.data:
            try:
                pgr_documento_id = int(self.data.get('pgr_documento'))
                self.fields['ges'].queryset = GESGrupoExposicao.objects.filter(pgr_documento_id=pgr_documento_id).order_by('nome')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.pgr_documento:
            self.fields['ges'].queryset = self.instance.pgr_documento.grupos_exposicao.order_by('nome')

        # Garante que o valor inicial vem no formato ISO
        if self.instance and self.instance.pk:
            for field_name in ['data_identificacao']:  # adicione outros campos date aqui
                if field_name in self.fields:
                    self.fields[field_name].widget.format = '%Y-%m-%d'

# ========================================
# FORMULÁRIO DE PLANO DE AÇÃO
# ========================================

class PlanoAcaoPGRForm(forms.ModelForm):
    """Formulário para planos de ação"""
    
    class Meta:
        model = PlanoAcaoPGR
        fields = [
            'risco_identificado', 'tipo_acao', 'descricao_acao',
            'justificativa', 'prioridade', 'responsavel', 'recursos_necessarios',
            'custo_estimado', 'data_prevista', 'data_conclusao', 'status',
            'resultado_obtido', 'eficacia_acao', 'observacoes'
        ]
        widgets = {
            'risco_identificado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_acao': forms.Select(attrs={'class': 'form-select'}),
            'descricao_acao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'justificativa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'recursos_necessarios': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'custo_estimado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_prevista': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_conclusao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'resultado_obtido': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'eficacia_acao': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        data_prevista = cleaned_data.get('data_prevista')
        data_conclusao = cleaned_data.get('data_conclusao')
        
        if data_conclusao and data_prevista:
            if data_conclusao < data_prevista:
                self.add_error('data_conclusao', 'A data de conclusão não pode ser anterior à data prevista.')
        
        return cleaned_data


# ========================================
# FORMULÁRIO DE CRONOGRAMA
# ========================================

class CronogramaAcaoPGRForm(forms.ModelForm):
    """Formulário para cronograma de ações"""

    class Meta:
        model = CronogramaAcaoPGR
        fields = [
            'pgr_documento',
            'numero_item',
            'acao_necessaria',
            'publico_alvo',
            'periodicidade',
            'responsavel',
            'data_proxima_avaliacao',
            'status',
            'data_realizacao',
            'observacoes',
        ]
        widgets = {
            'pgr_documento': forms.Select(attrs={'class': 'form-select'}),
            'numero_item': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'acao_necessaria': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'publico_alvo': forms.TextInput(attrs={'class': 'form-control'}),
            'periodicidade': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'data_proxima_avaliacao': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_realizacao': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se só existe UM documento PGR, seleciona automaticamente
        pgr_qs = PGRDocumento.objects.all()
        if pgr_qs.count() == 1:
            self.fields['pgr_documento'].initial = pgr_qs.first()

    def clean(self):
        cleaned_data = super().clean()
        pgr_documento = cleaned_data.get('pgr_documento')
        numero_item = cleaned_data.get('numero_item')

        if pgr_documento and numero_item:
            # Verifica duplicata (ignora o próprio registro na edição)
            qs = CronogramaAcaoPGR.objects.filter(
                pgr_documento=pgr_documento,
                numero_item=numero_item
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    f'Já existe uma ação com o item nº {numero_item} '
                    f'neste documento PGR.'
                )

        # Validar datas
        data_realizacao = cleaned_data.get('data_realizacao')
        status = cleaned_data.get('status')

        if status == 'concluido' and not data_realizacao:
            self.add_error(
                'data_realizacao',
                'Informe a data de realização para ações concluídas.'
            )

        return cleaned_data

# ========================================
# FORMULÁRIO DE REVISÃO
# ========================================

class PGRRevisaoForm(forms.ModelForm):
    """Formulário para revisões do PGR"""
    
    class Meta:
        model = PGRRevisao
        fields = [
            'pgr_documento', 'numero_revisao', 'descricao_revisao',
            'motivo', 'data_realizacao', 'realizada_por', 'observacoes'
        ]
        widgets = {
            'pgr_documento': forms.Select(attrs={'class': 'form-select'}),
            'numero_revisao': forms.NumberInput(attrs={'class': 'form-control'}),
            'descricao_revisao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'data_realizacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'format': '%Y-%m-%d'}),
            'realizada_por': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


# ========================================
# FORMULÁRIO DE AVALIAÇÃO QUANTITATIVA
# ========================================

class AvaliacaoQuantitativaForm(forms.ModelForm):
    """Formulário para avaliações quantitativas"""
    
    class Meta:
        model = AvaliacaoQuantitativa
        fields = [
            'risco_identificado', 'tipo_avaliacao', 'data_avaliacao',
            'resultado_medido', 'unidade_medida', 'limite_tolerancia_nr',
            'conforme', 'metodologia_utilizada', 'equipamento_utilizado',
            'responsavel_avaliacao', 'observacoes'
        ]
        widgets = {
            'risco_identificado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_avaliacao': forms.Select(attrs={'class': 'form-select'}),
            'data_avaliacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'resultado_medido': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'limite_tolerancia_nr': forms.TextInput(attrs={'class': 'form-control'}),
            'conforme': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'metodologia_utilizada': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'equipamento_utilizado': forms.TextInput(attrs={'class': 'form-control'}),
            'responsavel_avaliacao': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class AcompanhamentoPlanoAcaoForm(forms.ModelForm):
    """
    Formulário para UMA ÚNICA entrada de acompanhamento.
    """
    class Meta:
        model = AcompanhamentoPlanoAcao
        fields = [
            'data_acompanhamento', 'status_atual', 'descricao', 
            'percentual_conclusao', 'responsavel_acompanhamento',
            'dificuldades', 'proximos_passos', 'arquivo_evidencia'
        ]
        widgets = {
            'data_acompanhamento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status_atual': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descreva o progresso...', 'class': 'form-control'}),
            'percentual_conclusao': forms.NumberInput(attrs={'min': 0, 'max': 100, 'class': 'form-control'}),
            'responsavel_acompanhamento': forms.TextInput(attrs={'placeholder': 'Nome do responsável...', 'class': 'form-control'}),
            'dificuldades': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'proximos_passos': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'arquivo_evidencia': forms.FileInput(attrs={'class': 'form-control'}),
        }

# 3. Formulário para o Plano de Ação (o modelo PAI)
#    A lógica de validação do status e prazo pertence aqui.
class PlanoAcaoPGRForm(forms.ModelForm):
    """
    Formulário para criar e editar um Plano de Ação PGR.
    """
    class Meta:
        model = PlanoAcaoPGR
        fields = [
            'risco_identificado', 'tipo_acao', 'descricao_acao', 'prioridade',
            'data_prevista', 'responsavel', 'custo_estimado', 'status', 'data_conclusao',
            'observacoes'
        ]
        widgets = {
            'risco_identificado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_acao': forms.Select(attrs={'class': 'form-select'}),
            'descricao_acao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
            'data_prevista': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_conclusao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'custo_estimado': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Permite passar um risco inicial pela URL
        risco_inicial = kwargs.pop('risco_inicial', None)
        super().__init__(*args, **kwargs)
        
        if risco_inicial:
            self.fields['risco_identificado'].initial = risco_inicial
            # Limita as opções de risco se um já foi pré-selecionado
            self.fields['risco_identificado'].queryset = RiscoIdentificado.objects.filter(pk=risco_inicial)