# departamento_pessoal/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from .models import (
    Funcionarios, 
    Admissao, 
    Documentos, 
    Cargos, 
    Departamentos, 
    Cbos
)
from .validators import validate_cpf, validate_pis

# --- Formulários Principais (Refatorados) ---

class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionarios
        fields = ['nome', 'data_nascimento', 'naturalidade', 'telefone', 'email', 'sexo', 'estatus']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'data_nascimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'naturalidade': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'estatus': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = { 'estatus': 'Status', 'sexo': 'Gênero' }

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if telefone:
            telefone_digits = ''.join(filter(str.isdigit, telefone))
            if len(telefone_digits) not in [10, 11]:
                raise ValidationError('Telefone deve conter 10 ou 11 dígitos (DDD + número).')
            return telefone_digits
        return telefone

class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documentos
        fields = [
            'tipo', 'cpf', 'pis', 'ctps', 'rg', 'uf_emissor_rg', 
            'orgao_emissor_rg', 'reservista', 'titulo_eleitor', 'anexo'
        ]
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
            'pis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.00000.00-0'}),
            'ctps': forms.TextInput(attrs={'class': 'form-control'}),
            'rg': forms.TextInput(attrs={'class': 'form-control'}),
            'uf_emissor_rg': forms.Select(attrs={'class': 'form-select'}),
            'orgao_emissor_rg': forms.TextInput(attrs={'class': 'form-control'}),
            'reservista': forms.TextInput(attrs={'class': 'form-control'}),
            'titulo_eleitor': forms.TextInput(attrs={'class': 'form-control'}),
            'anexo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.funcionario = kwargs.pop('funcionario', None)
        super().__init__(*args, **kwargs)
        self.fields['anexo'].validators.append(
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])
        )

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        return ''.join(filter(str.isdigit, cpf)) if cpf else cpf

    def clean_pis(self):
        pis = self.cleaned_data.get('pis')
        return ''.join(filter(str.isdigit, pis)) if pis else pis

class AdmissaoForm(forms.ModelForm):
    dias_semana = forms.MultipleChoiceField(
        choices=Admissao.DIAS_SEMANA_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Dias de Trabalho"
    )
    
    class Meta:
        model = Admissao
        exclude = ['funcionario'] 
        widgets = {
            'data_admissao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_demissao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hora_entrada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_saida': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'departamento': forms.Select(attrs={'class': 'form-select'}),
            'matricula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Deixe em branco para gerar automaticamente'}),
            'salario': forms.NumberInput(attrs={'class': 'form-control'}),
            'tipo_contrato': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.dias_semana:
            self.initial['dias_semana'] = self.instance.dias_semana.split(',')
        self.fields['matricula'].required = False

    def clean_dias_semana(self):
        return ','.join(self.cleaned_data.get('dias_semana', []))

# --- Formulários Auxiliares (Faltantes) ---
# CORREÇÃO: Adicionando os formulários que estavam faltando.

class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamentos
        fields = ['nome', 'sigla', 'tipo', 'centro_custo', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do departamento'}),
            'sigla': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sigla (ex: RH, TI)', 'maxlength': '5'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'centro_custo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código do centro de custo'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {'ativo': 'Departamento ativo?'}

class CboForm(forms.ModelForm):
    class Meta:
        model = Cbos
        fields = ['codigo', 'titulo', 'descricao']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código CBO'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título da ocupação'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição detalhada da ocupação'}),
        }

class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargos
        fields = ['nome', 'cbo', 'salario_base', 'descricao', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do cargo'}),
            'cbo': forms.Select(attrs={'class': 'form-select'}),
            'salario_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição das atribuições do cargo'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {'ativo': 'Cargo ativo?'}
