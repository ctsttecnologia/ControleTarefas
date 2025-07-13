# departamento_pessoal/forms.py

# departamento_pessoal/forms.py (VERSÃO FINAL E COMPLETA)

from django import forms
from django.contrib.auth import get_user_model
from .models import Funcionario, Documento, Cargo, Departamento


User = get_user_model()

# --- Formulários para Modelos de Apoio (Cargo e Departamento) ---

class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['nome', 'centro_custo', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'centro_custo': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

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
    class Meta:
        model = Funcionario
        # Lista todos os campos que o usuário pode preencher no formulário
        fields = [
            'usuario', 'nome_completo', 'email_pessoal', 'telefone', 'data_nascimento', 'sexo',
            'matricula', 'departamento', 'cargo', 'data_admissao', 'salario', 'status', 'data_demissao', 'cliente',
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
        super().__init__(*args, **kwargs)

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
        fields = ['funcionario', 'tipo', 'numero', 'anexo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deixa o campo de funcionário mais amigável
        self.fields['funcionario'].queryset = Funcionario.objects.order_by('nome_completo')
        self.fields['funcionario'].empty_label = "Selecione um funcionário"

        # Aplica classes do bootstrap para um visual consistente
        self.fields['funcionario'].widget.attrs.update({'class': 'form-select'})
        self.fields['tipo'].widget.attrs.update({'class': 'form-select'})
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
