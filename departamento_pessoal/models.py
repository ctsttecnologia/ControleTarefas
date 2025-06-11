
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator, FileExtensionValidator

from logradouro.constant import ESTADOS_BRASIL

class Departamentos(models.Model):


    TIPO_DEPARTAMENTO_CHOICES = [
        ('ADM', 'Administrativo'),
        ('OPR', 'Operacional'),
        ('COM', 'Comercial'),
        ('FIN', 'Financeiro'),
        ('RH', 'Recursos Humanos'),
        ('PCM', 'Planejamento'),
        ('TST', 'Segurança do Trabalho'),
        ('DP', 'Departamento Pessoal'),
    ]
    
    nome = models.CharField(max_length=50, unique=True, verbose_name=_('Nome do Departamento'))
    sigla = models.CharField(max_length=10, unique=True, verbose_name=_('Sigla'))
    tipo = models.CharField(max_length=3, choices=TIPO_DEPARTAMENTO_CHOICES, default='ADM')
    centro_custo = models.CharField(max_length=20, unique=True, blank=True, null=True)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateField(default=timezone.now)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departamentos'
        verbose_name = _('Departamento')
        verbose_name_plural = _('Departamentos')
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.sigla})"
   
    @property
    def departamento_field(self):
        Departamentos = apps.get_model('departamentos', 'Departamentos')
        return models.ForeignKey(
            Departamentos,
            on_delete=models.SET_NULL,
            null=True,
            blank=True
        )
    
    departamento = departamento_field

class Cbos(models.Model):
    codigo = models.CharField(max_length=6, unique=True, verbose_name=_('Código CBO'))
    titulo = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    data_atualizacao = models.DateField(auto_now=True)

    class Meta:
        db_table = 'cbos'
        verbose_name = _('CBO')
        verbose_name_plural = _('CBOs')
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.titulo}"

class Cargos(models.Model):
    nome = models.CharField(max_length=50, unique=True, verbose_name=_('Nome do Cargo'))
    cbo = models.ForeignKey(Cbos, on_delete=models.PROTECT, related_name='cargos')
    salario_base = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'cargos'
        verbose_name = _('Cargo')
        verbose_name_plural = _('Cargos')
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} (R$ {self.salario_base})"

class Funcionarios(models.Model):
    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro'),
    ]
    
    ESTATUS_CHOICES = [
        (1, 'Ativo'),
        (2, 'Afastado'),
        (3, 'Desligado'),
        (4, 'Férias'),
    ]

    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=15, blank=True)
    naturalidade = models.CharField(max_length=30, blank=True)
    data_nascimento = models.DateField()
    email = models.EmailField(unique=True)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    estatus = models.IntegerField(choices=ESTATUS_CHOICES, default=1)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    logradouro = models.ForeignKey('logradouro.Logradouro', on_delete=models.PROTECT, null=True, blank=True)
    
    # Adicionado relacionamento com Documentos
    documentos = models.OneToOneField(
        'Documentos',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='funcionario_documentos'
    )

    class Meta:
        db_table = 'funcionarios'
        verbose_name = _('Funcionário')
        verbose_name_plural = _('Funcionários')
        ordering = ['nome']
    
    def __str__(self):
        matricula = self.matricula if hasattr(self, 'admissao') else 'Sem matrícula'
        return f"{self.nome} ({matricula})"

    @property
    def idade(self):
        hoje = timezone.now().date()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < 
            (self.data_nascimento.month, self.data_nascimento.day)
        )

    @property
    def matricula(self):
        return self.admissao.matricula if hasattr(self, 'admissao') else None
    
    def save(self, *args, **kwargs):
        """Remove formatação antes de salvar"""
        if self.telefone:
            self.telefone = ''.join(filter(str.isdigit, str(self.telefone)))
        super().save(*args, **kwargs)
    
    @property
    def telefone_formatado(self):
        """Retorna o telefone formatado para exibição"""
        if not self.telefone:
            return "-"
        tel = str(self.telefone)
        if len(tel) == 11:
            return '({}) {}-{}'.format(tel[:2], tel[2:7], tel[7:])
        elif len(tel) == 10:
            return '({}) {}-{}'.format(tel[:2], tel[2:6], tel[6:])
        return tel

class Admissao(models.Model):
    TIPO_CONTRATO_CHOICES = [
        ('CLT', 'Registro CLT'),
        ('PJ', 'Pessoa Jurídica'),
        ('EST', 'Estagiário'),
        ('APR', 'Aprendiz'),
    ]
    
    DIAS_SEMANA_CHOICES = [
        ('SEG', 'Segunda-feira'),
        ('TER', 'Terça-feira'),
        ('QUA', 'Quarta-feira'),
        ('QUI', 'Quinta-feira'),    
        ('SEX', 'Sexta-feira'),
        ('SAB', 'Sábado'),
        ('DOM', 'Domingo'),
    ]
    
    funcionario = models.OneToOneField(Funcionarios, on_delete=models.CASCADE, related_name='admissao')
    cargo = models.ForeignKey(Cargos, on_delete=models.PROTECT, related_name='admissoes')
    departamento = models.ForeignKey(Departamentos, on_delete=models.PROTECT, related_name='admissoes')
    matricula = models.CharField(max_length=10, unique=True)
    data_admissao = models.DateField(default=timezone.now)
    salario = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_contrato = models.CharField(max_length=3, choices=TIPO_CONTRATO_CHOICES, default='CLT')
    data_demissao = models.DateField(null=True, blank=True)
    hora_entrada = models.TimeField(verbose_name='Horário de entrada', null=True, blank=True)
    hora_saida = models.TimeField(verbose_name='Horário de saída', null=True, blank=True)
    dias_trabalhado =  models.CharField(max_length=27, blank=True)
    dias_semana = models.CharField(max_length=1, blank=True)

    class Meta:
        db_table = 'admissao'
        verbose_name = 'Admissão'
        verbose_name_plural = 'Admissões'
        ordering = ['-data_admissao']

    def __str__(self):
        return f"{self.matricula} - {self.funcionario.nome}"

    @property
    def tempo_empresa(self):
        end_date = self.data_demissao or timezone.now().date()
        delta = end_date - self.data_admissao
        return delta.days // 30

    def get_dias_semana_display(self):
        if not self.dias_semana:
            return "Nenhum dia selecionado"
        
        dias_map = dict(self.DIAS_SEMANA_CHOICES)
        dias = [dias_map[code] for code in self.dias_semana.split(',') if code in dias_map]
        return ', '.join(dias) or "Nenhum dia válido selecionado"

class Documentos(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
        ('ME', 'MEI'),
    ]

    rg_regex = RegexValidator(
        regex=r'^\d{2}\.\d{3}\.\d{3}-[\dX]$|^\d{9}$',
        message="RG inválido. Formato esperado: 00.000.000-0 ou 00.000.000-X."
    )
    
    # Alterado para OneToOneField para manter consistência com o campo em Funcionarios
    funcionario = models.OneToOneField(
        Funcionarios,
        on_delete=models.CASCADE,
        related_name='documentos_funcionario'
    )
    
    nome = models.CharField(max_length=50, blank=True) 
    sigla = models.CharField(max_length=10, blank=True)
    tipo = models.CharField(max_length=3, choices=TIPO_DOCUMENTO_CHOICES, blank=True)
    cpf = models.CharField(max_length=14, unique=True, verbose_name=_('CPF'))
    pis = models.CharField(max_length=14, unique=True, verbose_name=_('PIS/PASEP'), blank=True)
    rg = models.CharField(
        max_length=10, 
        unique=True, 
        verbose_name=_('RG'),
        validators=[
            MinLengthValidator(8, message="RG deve ter no mínimo 8 dígitos"),
            rg_regex
        ]
    )
    emissor = models.CharField(max_length=6, verbose_name=_('Orgão Emissor'), blank=True)
    uf = models.CharField(
        max_length=2,
        choices=ESTADOS_BRASIL,
        blank=True,
        default=''
    )
    ctps = models.CharField(max_length=11, blank=True, null=True)
    reservista = models.CharField(max_length=12, verbose_name=_('Certificado de Reservista'), blank=True)
    titulo_eleitor = models.CharField(max_length=15, verbose_name=_('Título de Eleitor'), blank=True)
    anexo_cpf = models.FileField(upload_to='documentos/cpf/', max_length=100, blank=True, null=True)
    anexo_ctps = models.FileField(upload_to='documentos/ctps/', max_length=100, blank=True, null=True)
    anexo_pis = models.FileField(upload_to='documentos/pis/', max_length=100, blank=True, null=True)
    anexo_rg = models.FileField(upload_to='documentos/rg/', max_length=100, blank=True, null=True)
    centro_custo = models.CharField(max_length=20, blank=True)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documentos'
        verbose_name = _('Documento')
        verbose_name_plural = _('Documentos Pessoais')
        unique_together = ['nome', 'sigla']

    def __str__(self):
        return f"Documentos de {self.funcionario.nome}"

    @property
    def cpf_formatado(self):
        if not self.cpf:
            return ""
        return f"{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}"

    @property
    def rg_formatado(self):
        if not self.rg:
            return ""
        return f"{self.rg[:2]}.{self.rg[2:5]}.{self.rg[5:8]}-{self.rg[8:]}" if len(self.rg) > 8 else self.rg
        
    def clean_rg(self):
        rg = self.cleaned_data.get('rg')
        if rg:
            digitos = sum(c.isdigit() for c in rg)
            if digitos < 8:  # 8 dígitos + dígito verificador (que pode ser letra)
                raise ValidationError("RG deve conter pelo menos 8 dígitos numéricos")
        return rg

    @property
    def pis_formatado(self):
        if not self.pis:
            return ""
        return f"{self.pis[:3]}.{self.pis[3:8]}.{self.pis[8:10]}-{self.pis[10:]}"



