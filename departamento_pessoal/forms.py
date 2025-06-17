from django import forms
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, RegexValidator, MinLengthValidator, RegexValidator, FileExtensionValidator

from .models import Funcionarios, Admissao, Documentos, Cargos, Departamentos, Cbos
from localflavor.br.forms import BRStateSelect
import re  # Para usar expressões regulares na validação


from logradouro.constant import ESTADOS_BRASIL

class FuncionarioForm(forms.ModelForm):
    telefone = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control telefone-mask',
            'placeholder': '(00) 00000-0000'
        }),
        max_length=15,
        required=False,
        help_text="Formato: (DDD) 99999-9999"
    )

    class Meta:
        model = Funcionarios
        fields = ['nome', 'data_nascimento', 'naturalidade', 'telefone', 'email', 'sexo', 'estatus']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'data_nascimento': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'naturalidade': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'sexo': forms.Select(attrs={'class': 'form-control'}),
            'estatus': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'estatus': 'Status',
            'sexo': 'Gênero'
        }

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if telefone:
            telefone = ''.join(filter(str.isdigit, telefone))
            if len(telefone) not in [10, 11]:
                raise ValidationError('Telefone deve conter 10 ou 11 dígitos (incluindo DDD)')
            if len(telefone) == 11:
                return '({}) {}-{}'.format(telefone[:2], telefone[2:7], telefone[7:])
            elif len(telefone) == 10:
                return '({}) {}-{}'.format(telefone[:2], telefone[2:6], telefone[6:])
        return telefone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError('Por favor, insira um endereço de email válido')
        return email

class AdmissaoForm(forms.ModelForm):
    dias_semana = forms.MultipleChoiceField(
        choices=Admissao.DIAS_SEMANA_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Admissao
        fields = '__all__'
        widgets = {
            'funcionario': forms.HiddenInput(),
            'data_admissao': forms.DateInput(attrs={'type': 'date'}),
            'data_demissao': forms.DateInput(attrs={'type': 'date'}),
            'hora_entrada': forms.TimeInput(attrs={'type': 'time'}),
            'hora_saida': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.dias_semana:
            self.initial['dias_semana'] = self.instance.dias_semana.split(',')

    def clean_dias_semana(self):
        data = self.cleaned_data.get('dias_semana', [])
        return ','.join(data)

class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documentos
        fields = '__all__'
        widgets = {
            'data_criacao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'uf': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'sigla': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control cpf-mask'}),
            'pis': forms.TextInput(attrs={'class': 'form-control pis-mask'}),
            'ctps': forms.TextInput(attrs={'class': 'form-control ctps-mask'}),
            'rg': forms.TextInput(attrs={'class': 'form-control'}),
            'emissor': forms.TextInput(attrs={'class': 'form-control'}),
            'reservista': forms.TextInput(attrs={'class': 'form-control'}),
            'titulo_eleitor': forms.TextInput(attrs={'class': 'form-control'}),
            'anexo_cpf': forms.FileInput(attrs={'class': 'form-control'}),
            'anexo_ctps': forms.FileInput(attrs={'class': 'form-control'}),
            'anexo_pis': forms.FileInput(attrs={'class': 'form-control'}),
            'anexo_rg': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configuração do centro_custo
        self.fields['centro_custo'].required = False
        self.fields['centro_custo'].label = "Centro de Custo"
        self.fields['centro_custo'].widget.attrs.update({'class': 'form-select'})
        
        # Adicionando validações de arquivo
        self.fields['anexo_cpf'].validators.append(
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])
        )
        self.fields['anexo_ctps'].validators.append(
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])
        )
        self.fields['anexo_pis'].validators.append(
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])
        )
        self.fields['anexo_rg'].validators.append(
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])
        )
        
        # Adicionando placeholders
        self.fields['cpf'].widget.attrs.update({'placeholder': '999.999.999-99'})
        self.fields['pis'].widget.attrs.update({'placeholder': '999.99999.99-9'})
        self.fields['ctps'].widget.attrs.update({'placeholder': '9999999/99'})
        
        # Tornando campos obrigatórios condicionalmente
        if self.instance and self.instance.tipo:
            self.set_required_fields(self.instance.tipo)
    
    def set_required_fields(self, tipo_documento):
        required_fields = {
            'CPF': ['cpf', 'anexo_cpf'],
            'PIS': ['pis', 'anexo_pis'],
            'CTPS': ['ctps', 'anexo_ctps'],
            'RG': ['rg', 'uf', 'emissor', 'anexo_rg'],
            'RES': ['reservista'],
            'TIT': ['titulo_eleitor'],
        }
        # Implementação da lógica para tornar campos obrigatórios
        fields_to_require = required_fields.get(tipo_documento, [])
        for field_name in fields_to_require:
            if field_name in self.fields:
                self.fields[field_name].required = True
        
    #Classe base com funcionalidades comuns a ambos os formulários """
    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        cpf_numeros = ''.join(filter(str.isdigit, cpf))
        
        if len(cpf_numeros) != 11:
            raise ValidationError('CPF deve conter exatamente 11 dígitos')
        
        # Verifica se todos os dígitos são iguais
        if len(set(cpf_numeros)) == 1:
            raise ValidationError('CPF inválido (todos dígitos iguais)')
        
        # Validação dos dígitos verificadores
        def calcula_digito(dados, fatores):
            total = sum(int(d) * f for d, f in zip(dados, fatores))
            resto = total % 11
            return 0 if resto < 2 else 11 - resto
        
        # Primeiro dígito verificador
        digito1 = calcula_digito(cpf_numeros[:9], range(10, 1, -1))
        if digito1 != int(cpf_numeros[9]):
            raise ValidationError('CPF inválido - primeiro dígito verificador incorreto')
        
        # Segundo dígito verificador
        digito2 = calcula_digito(cpf_numeros[:10], range(11, 1, -1))
        if digito2 != int(cpf_numeros[10]):
            raise ValidationError('CPF inválido - segundo dígito verificador incorreto')
        
        return f'{cpf_numeros[:3]}.{cpf_numeros[3:6]}.{cpf_numeros[6:9]}-{cpf_numeros[9:]}'

    def clean_rg(self):
        rg = self.cleaned_data.get('rg', '')
        rg_clean = re.sub(r'[^0-9Xx]', '', rg).upper()
        
        if len(rg_clean) < 8:
            raise ValidationError("RG deve conter no mínimo 8 dígitos")
        
        if len(rg_clean) > 10:
            raise ValidationError("RG não pode ter mais que 10 caracteres (incluindo dígito verificador)")
            
        # Verifica dígito verificador (último caractere)
        if len(rg_clean) > 8 and not (rg_clean[-1].isdigit() or rg_clean[-1] == 'X'):
            raise ValidationError("Dígito verificador do RG inválido (deve ser número ou X)")
        
        return rg_clean

    def clean_pis(self):
        pis = self.cleaned_data.get('pis', '')
        if pis:
            pis_numeros = ''.join(filter(str.isdigit, pis))
            if len(pis_numeros) != 11:
                raise ValidationError('PIS/PASEP/NIT deve conter exatamente 11 dígitos')
            
            # Validação do dígito verificador do PIS
            multiplicadores = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
            total = sum(int(pis_numeros[i]) * multiplicadores[i] for i in range(10))
            resto = total % 11
            digito = 11 - resto if resto > 1 else 0
            
            if digito != int(pis_numeros[10]):
                raise ValidationError('PIS/PASEP/NIT inválido - dígito verificador incorreto')
            
            return f'{pis_numeros[:3]}.{pis_numeros[3:8]}.{pis_numeros[8:10]}-{pis_numeros[10]}'
        return pis

    def clean_titulo_eleitor(self):
        titulo = self.cleaned_data.get('titulo_eleitor', '')
        if titulo:
            titulo_numeros = ''.join(filter(str.isdigit, titulo))
            if len(titulo_numeros) != 12:
                raise ValidationError('Título de Eleitor deve conter exatamente 12 dígitos')
            
            # Validação básica do título (UF + sequencial + dígitos)
            uf = int(titulo_numeros[8:10])
            if uf < 1 or uf > 28:
                raise ValidationError('Código de UF no título de eleitor inválido')
            
            return titulo_numeros
        return titulo

    def clean_reservista(self):
        reservista = self.cleaned_data.get('reservista', '')
        if reservista:
            reservista_numeros = ''.join(filter(str.isdigit, reservista))
            if len(reservista_numeros) != 12:
                raise ValidationError('Certificado de Reservista deve conter exatamente 12 dígitos')
            return reservista_numeros
        return reservista

    def clean_ctps(self):
        ctps = self.cleaned_data.get('ctps', '')
        if ctps:
            ctps_numeros = ''.join(filter(str.isdigit, ctps))
            if len(ctps_numeros) < 7 or len(ctps_numeros) > 11:
                raise ValidationError('CTPS deve ter entre 7 e 11 dígitos')
            return ctps_numeros
        return ctps

    def clean_anexo_cpf(self):
        return self._clean_anexo('anexo_cpf')

    def clean_anexo_rg(self):
        return self._clean_anexo('anexo_rg')

    def clean_anexo_pis(self):
        return self._clean_anexo('anexo_pis')

    def clean_anexo_ctps(self):
        return self._clean_anexo('anexo_ctps')

    def _clean_anexo(self, field_name):
        anexo = self.cleaned_data.get(field_name)
        if anexo:
            # Verifica tamanho máximo (5MB)
            if anexo.size > 5 * 1024 * 1024:
                raise ValidationError('O arquivo não pode exceder 5MB')
            
            # Verifica extensão
            ext = anexo.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                raise ValidationError('Formato de arquivo inválido. Use PDF, JPG ou PNG')
        return anexo

class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamentos
        fields = '__all__'
        fields = ['nome', 'sigla', 'tipo', 'centro_custo', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do departamento'
            }),
            'sigla': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sigla (ex: RH, TI)',
                'maxlength': '5'
            }),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'centro_custo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código do centro de custo'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'ativo': 'Departamento ativo?'
        }



class CboForm(forms.ModelForm):
    class Meta:
        model = Cbos
        fields = ['codigo', 'titulo', 'descricao']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código CBO'
            }),
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título da ocupação'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição detalhada da ocupação'
            }),
        }


class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargos
        fields = ['nome', 'cbo', 'salario_base', 'descricao', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do cargo'
            }),
            'cbo': forms.Select(attrs={'class': 'form-control'}),
            'salario_base': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição das atribuições do cargo'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'ativo': 'Cargo ativo?'
        }

