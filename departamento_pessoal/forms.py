from django import forms
from .models import Funcionarios, Admissao, Documentos, Cargos, Departamentos, Cbos

class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionarios
        fields = '__all__'
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_admissao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'placeholder': '(99) 99999-9999', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'pne': forms.Select(choices=[('S', 'Sim'), ('N', 'Não')], attrs={'class': 'form-control'}),
            'sexo': forms.Select(choices=[('M', 'Masculino'), ('F', 'Feminino')], attrs={'class': 'form-control'}),
            'peso': forms.NumberInput(attrs={'class': 'form-control'}),
            'altura': forms.NumberInput(attrs={'class': 'form-control'}),
            'estatus': forms.Select(choices=[(1, 'Ativo'), (0, 'Inativo')], attrs={'class': 'form-control'}),
            'logradouro': forms.Select(attrs={'class': 'form-control'}),
            'documentos': forms.Select(attrs={'class': 'form-control'}),
            'admissao': forms.Select(attrs={'class': 'form-control'}),
        }

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
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
            'pis': forms.TextInput(attrs={'class': 'form-control'}),
            'ctps': forms.TextInput(attrs={'class': 'form-control'}),
            'serie': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control'}),
            'rg': forms.TextInput(attrs={'class': 'form-control'}),
            'emissor': forms.TextInput(attrs={'class': 'form-control'}),
            'reservista': forms.NumberInput(attrs={'class': 'form-control'}),
            'titulo_eleitor': forms.NumberInput(attrs={'class': 'form-control'}),
        }

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