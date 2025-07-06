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
            'matricula', 'departamento', 'cargo', 'data_admissao', 'salario', 'status', 'data_demissao'
        ]
        # Aplica widgets para usar as classes do Bootstrap e tipos de input corretos
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
            'data_admissao': forms.DateInput(attrs={'type': 'date'}),
            'data_demissao': forms.DateInput(attrs={'type': 'date'}),
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
        # O campo 'funcionario' será preenchido automaticamente na view
        fields = ['tipo', 'numero', 'anexo']
