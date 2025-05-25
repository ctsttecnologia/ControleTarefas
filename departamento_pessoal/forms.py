from django import forms
from django.core.exceptions import ValidationError

from .models import Funcionarios, Admissao, Documentos, Cargos, Departamentos, Cbos
from .choices import CBO_CHOICES


def validate_unique_email(value):
    """Validador personalizado para verificar e-mail único"""
    if Funcionarios.objects.filter(email=value).exists():
        raise ValidationError('Este e-mail já está cadastrado')

class FuncionarioForm(forms.ModelForm):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        validators=[validate_unique_email]
    )

    class Meta:
        model = Funcionarios
        fields = ['nome', 'data_nascimento', 'naturalidade', 'telefone', 'email', 'sexo', 'estatus']
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control telefone-mask'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'sexo': forms.Select(attrs={'class': 'form-control'}),
            'estatus': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_telefone(self):
        """Validação personalizada para o telefone"""
        telefone = self.cleaned_data.get('telefone')
        # Remove todos os caracteres não numéricos
        telefone = ''.join(filter(str.isdigit, telefone))
        
        if len(telefone) not in [10, 11]:  # Verifica se tem 10 (sem 9º dígito) ou 11 dígitos
            raise ValidationError('Telefone deve conter 10 ou 11 dígitos (incluindo DDD)')
        
        return telefone

    def clean(self):
        """Validação cruzada entre campos"""
        cleaned_data = super().clean()
        # Adicione aqui quaisquer validações que dependam de múltiplos campos
        return cleaned_data     

    #Tratamento para validação do telefone
    telefone = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control telefone-mask',
            'placeholder': '(00) 00000-0000'
        }),
        max_length=15,
        required=False
    )

    class Meta:
        model = Funcionarios
        fields = ['nome', 'data_nascimento', 'naturalidade', 'telefone', 'email', 'sexo', 'estatus']

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if telefone:
            # Remove todos os caracteres não numéricos
            telefone = ''.join(filter(str.isdigit, telefone))
            
            if len(telefone) not in [10, 11]:  # Verifica se tem 10 ou 11 dígitos
                raise ValidationError('Telefone deve conter 10 ou 11 dígitos (incluindo DDD)')
            
            # Formata o telefone para (00) 00000-0000
            if len(telefone) == 11:
                return '({}) {}-{}'.format(telefone[:2], telefone[2:7], telefone[7:])
            elif len(telefone) == 10:
                return '({}) {}-{}'.format(telefone[:2], telefone[2:6], telefone[6:])
        
        return telefone

class AdmissaoForm(forms.ModelForm):
    class Meta:
        model = Admissao
        fields = '__all__'
        widgets = {
            'data_admissao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'matricula': forms.TextInput(attrs={'class': 'form-control'}),
            'salario': forms.NumberInput(attrs={'class': 'form-control'}),
            'cargo': forms.Select(attrs={'class': 'form-control'}),
            'departamento': forms.Select(attrs={'class': 'form-control'}),
        }

class DocumentosForm(forms.ModelForm):
    class Meta:
        model = Documentos
        fields = '__all__'
        widgets = {
            'cpf': forms.TextInput(attrs={'class': 'form-control cpf-mask'}),
            'pis': forms.TextInput(attrs={'class': 'form-control'}),
            'ctps': forms.TextInput(attrs={'class': 'form-control'}),
            'serie': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control'}),
            'rg': forms.TextInput(attrs={'class': 'form-control'}),
            'emissor': forms.TextInput(attrs={'class': 'form-control'}),
            'reservista': forms.TextInput(attrs={'class': 'form-control'}),
            'titulo_eleitor': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    # tratamento para cpf    
    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        
        # Verifica se o CPF tem 11 dígitos
        if len(cpf) != 11:
            raise ValidationError('CPF deve conter 11 dígitos')
        
        # Verifica se todos os dígitos são iguais (CPF inválido)
        if cpf == cpf[0] * 11:
            raise ValidationError('CPF inválido')
        
        # Cálculo do primeiro dígito verificador
        soma = 0
        for i in range(9):
            soma += int(cpf[i]) * (10 - i)
        resto = 11 - (soma % 11)
        if resto == 10 or resto == 11:
            resto = 0
        if resto != int(cpf[9]):
            raise ValidationError('CPF inválido')
        
        # Cálculo do segundo dígito verificador
        soma = 0
        for i in range(10):
            soma += int(cpf[i]) * (11 - i)
        resto = 11 - (soma % 11)
        if resto == 10 or resto == 11:
            resto = 0
        if resto != int(cpf[10]):
            raise ValidationError('CPF inválido')
        
        return cpf

class CargosForm(forms.ModelForm):
    class Meta:
        model = Cargos
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cbo': forms.Select(attrs={'class': 'form-control'}),
        }

class DepartamentosForm(forms.ModelForm):
    class Meta:
        model = Departamentos
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CbosForm(forms.ModelForm):
    class Meta:
        model = Cbos
        cbo = forms.ChoiceField(choices=CBO_CHOICES, label="Selecione um CBO")
        fields = '__all__'
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
        }




#Explicação dos Formulários
#FuncionarioForm:
#Campos como logradouro, documentos e admissao são renderizados como dropdowns (select), pois são chaves estrangeiras.
#Campos de data (data_nascimento, data_admissao) usam o tipo date do HTML5.
#Campos como pne, sexo e estatus usam dropdowns com opções pré-definidas.
#AdmissaoForm:
#Campos como cargo e departamento são renderizados como dropdowns, pois são chaves estrangeiras.
#O campo data_admissao usa o tipo date do HTML5.
#DocumentosForm:
#Todos os campos são renderizados como inputs de texto ou número.
#CargosForm:
#O campo cbo é renderizado como um dropdown, pois é uma chave estrangeira.
#DepartamentosForm:
#O campo nome é renderizado como um input de texto.
#CbosForm:
#Os campos codigo e descricao são renderizados como inputs de texto.