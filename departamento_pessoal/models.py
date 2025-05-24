from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from logradouro.models import Logradouro  # Importação correta
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class Departamentos(models.Model):
    TIPO_DEPARTAMENTO_CHOICES = [
        ('ADM', 'Administrativo'),
        ('OPR', 'Operacional'),
        ('COM', 'Comercial'),
        ('FIN', 'Financeiro'),
        ('RH', 'Recursos Humanos'),
        ('PCM', 'Planejamento'),
        ('TST', 'Seguraça do Trabalho'),
        ('DP', 'Departamento Pessoal'),

    ]
    
    nome = models.CharField(
        unique=True,
        max_length=50,
        verbose_name=_('Nome do Departamento'),
        help_text=_('Nome completo do departamento')
    )
    
    sigla = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_('Sigla'),
        help_text=_('Sigla abreviada do departamento')
    )
    
    tipo = models.CharField(
        max_length=3,
        choices=TIPO_DEPARTAMENTO_CHOICES,
        default='OUT',
        verbose_name=_('Tipo de Departamento')
    )
    
    data_criacao = models.DateField(
        verbose_name=_('Data de Criação'),
        default=timezone.now
    )
    
    ativo = models.BooleanField(
        default=True,
        verbose_name=_('Departamento Ativo?')
    )
    
    centro_custo = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_('Centro de Custo'),
        help_text=_('Código do centro de custo associado')
    )
    
     
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Atualização')
    )

    # Métodos avançados
    def clean(self):
        """Validações personalizadas"""
        super().clean()
        
        # Validação da sigla
        if not self.sigla.isalpha():
            raise ValidationError({
                'sigla': _('A sigla deve conter apenas letras.')
            })
        
        # Validação do nome
        if len(self.nome.split()) < 2:
            raise ValidationError({
                'nome': _('Informe o nome completo do departamento.')
            })

    def save(self, *args, **kwargs):
        """Garante validações antes de salvar"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def total_funcionarios(self):
        """Retorna o número total de funcionários no departamento"""
        if hasattr(self, 'admissoes'):
            return self.admissoes.filter(funcionario__estatus=1).count()
        return 0
    
    @property
    def orcamento_disponivel(self):
        """Método placeholder para cálculo de orçamento"""
        # Implementação real dependeria de integração com sistema financeiro
        return 0
    
    def ativar(self):
        """Ativa o departamento"""
        self.ativo = True
        self.save()
    
    def desativar(self):
        """Desativa o departamento"""
        self.ativo = False
        self.save()
    
    def __str__(self):
        return f"{self.nome} ({self.sigla})"
    
    class Meta:
        db_table = 'departamentos'
        verbose_name = _('Departamento')
        verbose_name_plural = _('Departamentos')
        ordering = ['nome']
        indexes = [
            models.Index(fields=['nome'], name='idx_departamento_nome'),
            models.Index(fields=['sigla'], name='idx_departamento_sigla'),
            models.Index(fields=['tipo'], name='idx_departamento_tipo'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['nome', 'sigla'],
                name='unique_departamento_nome_sigla'
            ),
        ]

    # Métodos
    def clean(self):
        """Validações adicionais"""
        super().clean()
        if self.cpf == '00000000000':
            raise ValidationError({'cpf': _('CPF inválido')})

    @property
    def cpf_formatado(self):
        """Formata o CPF para exibição"""
        return f"{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}"

    class Meta:
        db_table = 'documentos'
        verbose_name = _('Documento Pessoal')
        verbose_name_plural = _('Documentos Pessoais')
   

class Documentos(models.Model):
    # Validadores
    cpf_validator = RegexValidator(
        regex=r'^\d{11}$',
        message=_('CPF deve conter exatamente 11 dígitos')
    )
    pis_validator = RegexValidator(
        regex=r'^\d{11,12}$',
        message=_('PIS deve conter 11 ou 12 dígitos')
    )
    ctps_validator = RegexValidator(
        regex=r'^[A-Za-z0-9]{5,10}$',
        message=_('CTPS deve conter entre 5 e 10 caracteres alfanuméricos')
    )
    uf_validator = RegexValidator(
        regex=r'^[A-Z]{2}$',
        message=_('UF deve ser a sigla de 2 letras maiúsculas')
    )

    # Campos
    cpf = models.CharField(
        unique=True,
        max_length=11,
        validators=[cpf_validator],
        verbose_name=_('CPF'),
        help_text=_('11 dígitos')
    )
    pis = models.CharField(
        unique=True,
        max_length=12,
        validators=[pis_validator],
        verbose_name=_('PIS/PASEP'),
        help_text=_('11 ou 12 dígitos')
    )
    ctps = models.CharField(
        unique=True,
        max_length=10,
        validators=[ctps_validator],
        verbose_name=_('CTPS'),
        help_text=_('Número da Carteira de Trabalho')
    )
    serie = models.CharField(
        unique=True,
        max_length=10,
        verbose_name=_('Série')
    )
    uf = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        validators=[uf_validator],
        verbose_name=_('UF Emissor')
    )
    rg = models.CharField(
        unique=True,
        max_length=10,
        verbose_name=_('RG')
    )
    emissor = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name=_('Órgão Emissor')
    )
    reservista = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_('Certificado de Reservista')
    )
    titulo_eleitor = models.IntegerField(
        db_column='titulo_Eleitor',
        blank=True,
        null=True,
        verbose_name=_('Título de Eleitor')
    )

class Cbos(models.Model):
    codigo_validator = RegexValidator(
        regex=r'^\d{4}-\d{1}$',
        message=_('Formato do CBO deve ser XXXX-X')
    )

    codigo = models.CharField(
        unique=True,
        max_length=10,
        validators=[codigo_validator],
        verbose_name=_('Código CBO'),
        help_text=_('Formato: XXXX-X')
    )
    descricao = models.CharField(
        max_length=100,
        verbose_name=_('Descrição da Ocupação')
    )
    data_atualizacao = models.DateField(
        auto_now=True,
        verbose_name=_('Data de Atualização')
    )

    class Meta:
        db_table = 'cbos'
        verbose_name = _('Classificação Brasileira de Ocupações')
        verbose_name_plural = _('Classificações Brasileiras de Ocupações')
        ordering = ['codigo']

class Cargos(models.Model):
    nome = models.CharField(
        unique=True,
        max_length=50,
        verbose_name=_('Nome do Cargo')
    )
    cbo = models.ForeignKey(
        Cbos,
        models.PROTECT,
        related_name='cargos',
        verbose_name=_('Classificação CBO')
    )
    descricao = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name=_('Descrição Detalhada')
    )
    salario_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Salário Base')
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name=_('Cargo Ativo?')
    )

    def funcionarios_ativos(self):
        """Retorna quantidade de funcionários ativos no cargo"""
        return self.admissao.filter(funcionarios__estatus=1).count()

    def __str__(self):
        return f"{self.nome} ({self.cbo.codigo})"

    class Meta:
        db_table = 'cargos'
        verbose_name = _('Cargo')
        verbose_name_plural = _('Cargos')
        ordering = ['nome']

class Admissao(models.Model):
    TIPO_CONTRATO_CHOICES = [
        ('CLT', 'CLT'),
        ('PJ', 'Pessoa Jurídica'),
        ('EST', 'Estagiário'),
        ('APR', 'Aprendiz'),
    ]

    cargo = models.ForeignKey(
        Cargos,
        models.PROTECT,
        related_name='admissoes',
        verbose_name=_('Cargo')
    )
    departamento = models.ForeignKey(
        Departamentos,
        models.PROTECT,
        related_name='admissoes',
        verbose_name=_('Departamento')
    )
    data_admissao = models.DateField(
        db_column='data_Admissao',
        verbose_name=_('Data de Admissão')
    )
    matricula = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_('Matrícula')
    )
    salario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Salário')
    )
    tipo_contrato = models.CharField(
        max_length=3,
        choices=TIPO_CONTRATO_CHOICES,
        default='CLT',
        verbose_name=_('Tipo de Contrato')
    )
    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Data de Cadastro')
    )

    def clean(self):
        """Validações complexas da admissão"""
        super().clean()
        
        # Valida data de admissão
        if self.data_admissao > timezone.now().date():
            raise ValidationError({'data_admissao': _('Data de admissão não pode ser futura')})
        
        # Valida salário mínimo para o cargo
        if self.cargo.salario_base and self.salario < self.cargo.salario_base:
            raise ValidationError({
                'salario': _('Salário não pode ser menor que o base do cargo (R$ %s)') % self.cargo.salario_base
            })

    def save(self, *args, **kwargs):
        """Garante validação antes de salvar"""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def tempo_empresa(self):
        """Calcula tempo de empresa em meses"""
        delta = timezone.now().date() - self.data_admissao
        return round(delta.days / 30)

    class Meta:
        db_table = 'admissao'
        verbose_name = _('Admissão')
        verbose_name_plural = _('Admissões')
        ordering = ['-data_admissao']
        constraints = [
            models.UniqueConstraint(
                fields=['matricula'],
                name='unique_matricula'
            )
        ]


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

    logradouro = models.ForeignKey(
        Logradouro,
        models.PROTECT,
        null=True,
        blank=True,
        related_name='funcionarios',
        verbose_name=_('Endereço')
    )
    documentos = models.OneToOneField(
        Documentos,
        models.PROTECT,
        related_name='funcionario',
        verbose_name=_('Documentos')
    )
    admissao = models.OneToOneField(
        Admissao,
        models.PROTECT,
        related_name='funcionario',
        verbose_name=_('Dados de Admissão')
    )
    nome = models.CharField(
        max_length=100,
        verbose_name=_('Nome Completo')
    )
    data_nascimento = models.DateField(
        db_column='data_Nascimento',
        verbose_name=_('Data de Nascimento')
    )
    naturalidade = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name=_('Naturalidade')
    )
    telefone = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        verbose_name=_('Telefone')
    )
    email = models.EmailField(
        unique=True,
        verbose_name=_('E-mail')
    )
    sexo = models.CharField(
        max_length=1,
        choices=SEXO_CHOICES,
        verbose_name=_('Sexo')
    )
    estatus = models.IntegerField(
        choices=ESTATUS_CHOICES,
        default=1,
        verbose_name=_('Situação')
    )
    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Data de Cadastro')
    )

    # Métodos avançados
    @property
    def idade(self):
        """Calcula idade atual"""
        today = timezone.now().date()
        born = self.data_nascimento
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def promover(self, novo_cargo, novo_salario):
        """Promove funcionário para novo cargo"""
        self.admissao.cargo = novo_cargo
        self.admissao.salario = novo_salario
        self.admissao.save()

    class Meta:
        db_table = 'funcionarios'
        verbose_name = _('Funcionário')
        verbose_name_plural = _('Funcionários')
        ordering = ['nome']
        indexes = [
            models.Index(fields=['nome'], name='idx_funcionario_nome'),
            models.Index(fields=['estatus'], name='idx_funcionario_status'),
        ]







