from django import forms
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, RegexValidator, MinLengthValidator, RegexValidator

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

class DocumentosBaseForm(forms.ModelForm):
    """
    Classe base com funcionalidades comuns a ambos os formulários
    """
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


class DocumentosForm(DocumentosBaseForm):
    # Campos básicos
    cpf = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control cpf-mask',
            'placeholder': '000.000.000-00',
            'data-mask': '000.000.000-00'
        }),
        max_length=14,
        required=True,
        help_text="Informe o CPF no formato: 000.000.000-00"
    )
    
    rg = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control rg-mask',
            'placeholder': '00.000.000-0',
            'data-mask': '00.000.000-0'
        }),
        required=True,
        max_length=12,
        help_text="Formato: 00.000.000-0 (com dígito verificador)"
    )
    
    emissor = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'SSP'
        }),
        required=True,
        max_length=6,
        validators=[
            RegexValidator(
                r'^[A-Z]{2,6}$',
                message="Emissor deve conter apenas letras maiúsculas (2 a 6 caracteres)"
            )
        ]
    )
    
    uf = forms.ChoiceField(
        choices=ESTADOS_BRASIL,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': 'required'
        }),
        label='UF Emissor *',
        initial=''
    )
    
    # Documentos trabalhistas
    pis = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control pis-mask',
            'placeholder': '000.00000.00-0',
            'data-mask': '000.00000.00-0'
        }),
        required=False,
        max_length=14,
        help_text="Formato: 000.00000.00-0"
    )
    
    ctps = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control ctps-mask',
            'placeholder': '0000000',
            'data-mask': '0000000'
        }),
        required=False,
        max_length=7,
        help_text="Número da CTPS (apenas dígitos)"
    )
    
    # Documentos militares e eleitorais
    titulo_eleitor = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control titulo-mask',
            'placeholder': '000000000000',
            'data-mask': '000000000000'
        }),
        required=False,
        max_length=12,
        help_text="12 dígitos (sem pontos ou espaços)"
    )
    
    reservista = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control reservista-mask',
            'placeholder': '000000000000',
            'data-mask': '000000000000'
        }),
        required=False,
        max_length=12,
        help_text="12 dígitos (sem formatação)"
    )
    
    # Campos de anexos
    anexo_cpf = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'application/pdf,image/jpeg,image/png'
        }),
        required=False,
        help_text="Anexar cópia do CPF (PDF, JPG ou PNG, máximo 5MB)"
    )
    
    anexo_rg = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'application/pdf,image/jpeg,image/png'
        }),
        required=False,
        help_text="Anexar cópia do RG (PDF, JPG ou PNG, máximo 5MB)"
    )
    
    anexo_pis = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'application/pdf,image/jpeg,image/png'
        }),
        required=False,
        help_text="Anexar cópia do PIS (PDF, JPG ou PNG, máximo 5MB)"
    )
    
    anexo_ctps = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'application/pdf,image/jpeg,image/png'
        }),
        required=False,
        help_text="Anexar cópia da CTPS (PDF, JPG ou PNG, máximo 5MB)"
    )

    class Meta:
        model = Documentos
        fields = '__all__'
        widgets = {
            'uf': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configura classes CSS para todos os campos
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            
            # Configura campos obrigatórios
            if field_name in ['cpf', 'rg', 'emissor', 'uf']:
                field.required = True
                field.widget.attrs['required'] = 'required'


class DocumentosEditForm(DocumentosBaseForm):
    class Meta:
        db_table = 'documentos'
        model = Documentos
        fields = '__all__'
        exclude = ['funcionario', 'data_criacao', 'data_atualizacao']
        widgets = {
            'cpf': forms.TextInput(attrs={
                'class': 'form-control cpf-mask',
                'data-mask': '000.000.000-00',
                'placeholder': '000.000.000-00'
            }),
            'rg': forms.TextInput(attrs={
                'class': 'form-control rg-mask',
                'data-mask': '00.000.000-0',
                'placeholder': '00.000.000-0'
            }),
            'emissor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SSP'
            }),
            'uf': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'pis': forms.TextInput(attrs={
                'class': 'form-control pis-mask',
                'data-mask': '000.00000.00-0',
                'placeholder': '000.00000.00-0'
            }),
            'ctps': forms.TextInput(attrs={
                'class': 'form-control ctps-mask',
                'data-mask': '0000000',
                'placeholder': '0000000'
            }),
            'titulo_eleitor': forms.TextInput(attrs={
                'class': 'form-control titulo-mask',
                'data-mask': '000000000000',
                'placeholder': '000000000000'
            }),
            'reservista': forms.TextInput(attrs={
                'class': 'form-control reservista-mask',
                'data-mask': '000000000000',
                'placeholder': '000000000000'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['uf'].choices = ESTADOS_BRASIL
        
        # Configura campos obrigatórios
        for field in ['cpf', 'rg', 'emissor', 'uf']:
            self.fields[field].required = True
            self.fields[field].widget.attrs['required'] = 'required'
        
        # Configura campos de arquivo
        for field_name in ['anexo_cpf', 'anexo_rg', 'anexo_pis', 'anexo_ctps']:
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            })

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

