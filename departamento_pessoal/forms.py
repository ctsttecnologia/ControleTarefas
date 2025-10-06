# departamento_pessoal/forms.py

# departamento_pessoal/forms.py (VERSÃO FINAL E COMPLETA)

from django import forms
from django.contrib.auth import get_user_model

from seguranca_trabalho.models import Funcao
from .models import Funcionario, Documento, Cargo, Departamento


User = get_user_model()

# --- Formulários para Modelos de Apoio (Cargo e Departamento) ---

class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        # REMOVA 'filial' desta lista. O usuário não precisa mais interagir com este campo.
        fields = ['nome', 'centro_custo', 'ativo']

    def __init__(self, *args, **kwargs):
        # A lógica complexa de __init__ para filtrar o queryset não é mais necessária.
        super().__init__(*args, **kwargs)
        
        # Podemos manter a estilização dos widgets
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
    class Meta:
        model = Documento
        # Adicionamos 'funcionario' à lista de campos
        fields = ['funcionario', 'tipo_documento', 'numero', 'anexo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deixa o campo de funcionário mais amigável
        self.fields['funcionario'].queryset = Funcionario.objects.order_by('nome_completo')
        self.fields['funcionario'].empty_label = "Selecione um funcionário"

        # Aplica classes do bootstrap para um visual consistente
        self.fields['funcionario'].widget.attrs.update({'class': 'form-select'})
        self.fields['tipo_documento'].widget.attrs.update({'class': 'form-select'})
        self.fields['numero'].widget.attrs.update({'class': 'form-control'})
        self.fields['anexo'].widget.attrs.update({'class': 'form-control'})

        # Se o formulário for instanciado para um funcionário específico,
        # podemos esconder e pré-selecionar o campo.
        if 'initial' in kwargs and 'funcionario' in kwargs['initial']:
            self.fields['funcionario'].widget = forms.HiddenInput()

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
        label='Selecione a planilha de funcionários (.xlsx)',
        widget=forms.ClearableFileInput(attrs={'accept': '.xlsx'})
    )