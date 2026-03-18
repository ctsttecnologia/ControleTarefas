# departamento_pessoal/forms.py 

from django import forms
from django.contrib.auth import get_user_model

from seguranca_trabalho.models import Funcao
from .models import Funcionario, Documento, Cargo, Departamento


User = get_user_model()

# --- Formulários para Modelos de Apoio (Cargo e Departamento) ---

class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['registro', 'nome', 'centro_custo', 'ativo']

    def __init__(self, *args, **kwargs):
        # A lógica complexa de __init__ para filtrar o queryset não é mais necessária.
        super().__init__(*args, **kwargs)
        
        # Podemos manter a estilização dos widgets
        self.fields['registro'].widget.attrs.update({'placeholder': 'Ex: 000'})
        self.fields['nome'].widget.attrs.update({'placeholder': 'Ex: Contabilidade'})
        self.fields['centro_custo'].widget.attrs.update({'placeholder': 'Ex: 101.02'})

class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        fields = ['nome', 'cbo', 'descricao', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cbo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# --- Formulário Principal de Funcionário ---

class FuncionarioForm(forms.ModelForm):

    funcao = forms.ModelChoiceField(
        queryset=Funcao.objects.filter(ativo=True),
        required=False, # Torna o campo não obrigatório
        label="Função (SST)",
        help_text="Função desempenhada para fins de SST e Matriz de EPI."
    )

    class Meta:
        model = Funcionario
        # Lista todos os campos que o usuário pode preencher no formulário
        fields = [
            'foto_3x4', 'nome_completo', 'data_nascimento', 'email_pessoal', 
            'telefone', 'sexo', 'usuario', 'matricula', 'departamento', 
            'cargo', 'funcao', 'cliente', 'data_admissao', 'salario', 
            'status', 'data_demissao'
        ]
        # Aplica widgets para usar as classes do Bootstrap e tipos de input corretos
        widgets = {
            'data_nascimento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date'}
            ),
            'data_admissao': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date'}
            ),
            'data_demissao': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date'}
            ),
        }

    def __init__(self, *args, **kwargs):

        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request and hasattr(request, 'user') and hasattr(request.user, 'filial_ativa'):
            filial_ativa = request.user.filial_ativa
            if filial_ativa:
                # Filtra as opções de 'funcao' para a filial ativa do usuário
                self.fields['funcao'].queryset = Funcao.objects.filter(filial=filial_ativa, ativo=True)
                # Você pode adicionar filtros para outros campos aqui também, se necessário
                # Ex: self.fields['cargo'].queryset = Cargo.objects.filter(filial=filial_ativa)

        # Aplica a classe .form-control ou .form-select a todos os campos para consistência
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif not isinstance(field.widget, forms.DateInput): # DateInput já foi customizado
                field.widget.attrs.update({'class': 'form-control'})

        # Lógica inteligente para o campo 'usuario'
        if self.instance and self.instance.pk:
            # Se estiver EDITANDO um funcionário, não permite trocar o usuário do sistema associado.
            self.fields['usuario'].disabled = True
            self.fields['usuario'].help_text = 'Não é possível alterar o usuário de um funcionário existente.'
        else:
            # Se estiver CRIANDO, mostra apenas usuários que AINDA NÃO estão ligados a outro funcionário.
            usuarios_com_funcionario = Funcionario.objects.filter(usuario__isnull=False).values_list('usuario_id', flat=True)
            self.fields['usuario'].queryset = User.objects.exclude(pk__in=usuarios_com_funcionario).order_by('username')
            self.fields['usuario'].empty_label = "Selecione um Usuário do sistema para vincular"


# --- Formulário de Documentos ---

class DocumentoForm(forms.ModelForm):
    """
    Formulário inteligente que mostra/esconde campos conforme o tipo de documento.
    A lógica de exibição condicional fica no JavaScript do template.
    """

    class Meta:
        model = Documento
        fields = [
            # Comuns
            'funcionario', 'tipo_documento', 'numero',
            'data_emissao', 'data_validade',
            'orgao_expedidor', 'uf_expedidor',
            'observacoes', 'anexo',
            # RG
            'rg_nome_pai', 'rg_nome_mae', 'rg_naturalidade',
            # CNH
            'cnh_categoria', 'cnh_numero_registro',
            'cnh_primeira_habilitacao', 'cnh_observacoes_detran',
            # CTPS
            'ctps_serie', 'ctps_uf', 'ctps_digital',
            # Título
            'titulo_zona', 'titulo_secao', 'titulo_municipio',
            # Reservista
            'reservista_categoria', 'reservista_regiao_militar',
            # Registro de Classe
            'registro_orgao', 'registro_especialidade',
            # ASO
            'aso_tipo_exame', 'aso_apto', 'aso_medico_nome',
            'aso_medico_crm', 'aso_proximo_exame',
            # NR
            'nr_numero', 'nr_carga_horaria', 'nr_instituicao',
            # Certificado
            'certificado_nivel', 'certificado_curso', 'certificado_instituicao',
            # Passaporte
            'passaporte_pais_emissao',
            # Outro
            'outro_descricao',
        ]
        widgets = {
            'data_emissao': forms.DateInput(attrs={'type': 'date'}),
            'data_validade': forms.DateInput(attrs={'type': 'date'}),
            'cnh_primeira_habilitacao': forms.DateInput(attrs={'type': 'date'}),
            'aso_proximo_exame': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    # ── Mapeamento: tipo_documento → campos específicos ──
    CAMPOS_POR_TIPO = {
        'CPF': ['numero'],
        'RG': ['numero', 'data_emissao', 'orgao_expedidor', 'uf_expedidor',
                'rg_nome_pai', 'rg_nome_mae', 'rg_naturalidade'],
        'CNH': ['numero', 'cnh_categoria', 'cnh_numero_registro',
                 'data_emissao', 'data_validade', 'cnh_primeira_habilitacao',
                 'orgao_expedidor', 'uf_expedidor', 'cnh_observacoes_detran'],
        'CTPS': ['numero', 'ctps_serie', 'ctps_uf', 'ctps_digital', 'data_emissao'],
        'PIS': ['numero'],
        'TITULO': ['numero', 'titulo_zona', 'titulo_secao', 'titulo_municipio', 'uf_expedidor'],
        'RESERVISTA': ['numero', 'reservista_categoria', 'reservista_regiao_militar',
                       'orgao_expedidor', 'uf_expedidor'],
        'CERTIDAO_NASC': ['numero', 'data_emissao', 'orgao_expedidor', 'uf_expedidor'],
        'CERTIDAO_CAS': ['numero', 'data_emissao', 'orgao_expedidor', 'uf_expedidor'],
        'PASSAPORTE': ['numero', 'data_emissao', 'data_validade', 'passaporte_pais_emissao'],
        'RNE': ['numero', 'data_emissao', 'data_validade', 'orgao_expedidor'],
        'REGISTRO_CLASSE': ['numero', 'registro_orgao', 'registro_especialidade',
                            'data_emissao', 'data_validade', 'uf_expedidor'],
        'CERTIFICADO': ['certificado_nivel', 'certificado_curso',
                        'certificado_instituicao', 'data_emissao'],
        'ASO': ['aso_tipo_exame', 'aso_apto', 'aso_medico_nome',
                'aso_medico_crm', 'data_emissao', 'aso_proximo_exame'],
        'NR': ['nr_numero', 'nr_carga_horaria', 'nr_instituicao',
               'data_emissao', 'data_validade'],
        'COMPROVANTE_END': ['data_emissao'],
        'COMP_ESCOLAR': ['certificado_nivel', 'certificado_instituicao', 'data_emissao'],
        'OUTRO': ['numero', 'outro_descricao', 'data_emissao', 'data_validade'],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Funcionário
        self.fields['funcionario'].queryset = Funcionario.objects.order_by('nome_completo')
        self.fields['funcionario'].empty_label = 'Selecione um funcionário'

        # Bootstrap classes
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault('class', 'form-control')
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.setdefault('class', 'form-control')
            else:
                field.widget.attrs.setdefault('class', 'form-control')

        # Se funcionário pré-selecionado, esconde o campo
        if 'initial' in kwargs and kwargs['initial'].get('funcionario'):
            self.fields['funcionario'].widget = forms.HiddenInput()

        # Todos os campos específicos não-obrigatórios no form
        # (a obrigatoriedade é gerenciada no clean() do model)
        campos_especificos = set()
        for campos in self.CAMPOS_POR_TIPO.values():
            campos_especificos.update(campos)
        for campo in campos_especificos:
            if campo in self.fields:
                self.fields[campo].required = False


# NOVO FORMULÁRIO PARA O PROCESSO DE ADMISSÃO
class AdmissaoForm(forms.ModelForm):
    """
    Formulário focado em adicionar/editar os dados contratuais de um Funcionário.
    """
    class Meta:
        model = Funcionario
        # Campos específicos do processo de admissão/contrato
        fields = [
            'matricula', 'cargo', 'departamento', 'data_admissao', 
            'salario', 'status', 'data_demissao'
        ]
        widgets = {
            'data_admissao': forms.DateInput(attrs={'type': 'date'}),
            'data_demissao': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplica classes do Bootstrap para consistência
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif not isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control'})

        # Adiciona help_text para campos importantes
        self.fields['data_demissao'].help_text = "Preencha apenas se o status do funcionário for 'Inativo'."
        self.fields['matricula'].help_text = "Pode ser deixado em branco para geração automática (requer lógica na view ou model)."


class UploadFuncionariosForm(forms.Form):
    arquivo = forms.FileField(
        label='Selecione a planilha (.xlsx ou .csv)',
        widget=forms.ClearableFileInput(attrs={'accept': '.xlsx,.csv'})
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        ext = arquivo.name.split('.')[-1].lower()
        if ext not in ('xlsx', 'csv'):
            raise forms.ValidationError('Formato inválido. Envie um arquivo .xlsx ou .csv')
        # Limite de 10MB
        if arquivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError('O arquivo excede o limite de 10MB.')
        return arquivo
