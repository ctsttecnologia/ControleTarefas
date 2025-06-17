
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
        
    class Meta:
        db_table = 'funcionarios'
        verbose_name = _('Funcionário')
        verbose_name_plural = _('Funcionários')
        ordering = ['nome']
    
    def __str__(self):
        matricula = self.matricula if hasattr(self, 'admissao') and self.admissao else 'Sem matrícula'
        return f"{self.nome} ({matricula})"

    @property
    def documentos_do_funcionario(self):
        """Retorna todos os documentos associados a este funcionário"""
        return self.documentos.all()

    @property
    def documento_principal(self):
        """Retorna o documento principal (vinculado à admissão) se existir"""
        if hasattr(self, 'admissao') and self.admissao and self.admissao.documento_principal:
            return self.admissao.documento_principal
        return None

    @property
    def idade(self):
        hoje = timezone.now().date()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < 
            (self.data_nascimento.month, self.data_nascimento.day)
        )

    @property
    def matricula(self):
        if hasattr(self, 'admissao') and self.admissao:
            return self.admissao.matricula
        return "N/D"  # Ou None, conforme sua necessidade

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

class Documentos(models.Model):
    TIPO_CHOICES = [
        ('CLT', 'Registro CLT'),
        ('PJ', 'Pessoa Jurídica'),
        ('MEI', 'Micro-Empresa'),
    
    ]
    
    funcionario = models.ForeignKey(
        'Funcionarios',
        on_delete=models.CASCADE,
        related_name='documentos' # Isso permite funcionario.documentos.all()
    )
    nome = models.CharField(max_length=50, verbose_name='Nome do Documento')
    sigla = models.CharField(max_length=10, verbose_name='Sigla')
    tipo = models.CharField(max_length=4, choices=TIPO_CHOICES, verbose_name='Tipo de Contrato')
    data_criacao = models.DateField(verbose_name='Data de Criação')
    ativo = models.BooleanField(default=True, verbose_name='Ativo?')
    centro_custo = models.CharField(max_length=20, verbose_name='Centro de Custo')
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Última Atualização')
    
    # Campos específicos de documentos
    cpf = models.CharField(
        max_length=14, 
        blank=True, 
        null=True, 
        verbose_name='CPF',
        validators=[RegexValidator(
            regex=r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
            message='CPF deve estar no formato 000.000.000-00'
        )]
    )
    pis = models.CharField(
        max_length=14, 
        blank=True, 
        null=True, 
        verbose_name='PIS/PASEP',
        validators=[RegexValidator(
            regex=r'^\d{3}\.\d{5}\.\d{2}-\d{1}$',
            message='PIS deve estar no formato 000.00000.00-0'
        )]
    )
    ctps = models.CharField(
        max_length=11, 
        blank=True, 
        null=True, 
        verbose_name='CTPS',
        validators=[RegexValidator(
            regex=r'^\d{7}\/\d{2}$',
            message='CTPS deve estar no formato 0000000/00'
        )]
    )
    uf = models.CharField(
        max_length=2, 
        blank=True, 
        null=True, 
        choices=ESTADOS_BRASIL, 
        verbose_name='UF'
    )
    rg = models.CharField(
        max_length=10, 
        blank=True, 
        null=True, 
        verbose_name='RG'
    )
    emissor = models.CharField(
        max_length=6, 
        blank=True, 
        null=True, 
        verbose_name='Órgão Emissor'
    )
    reservista = models.CharField(
        max_length=12, 
        blank=True, 
        null=True, 
        verbose_name='Nº Reservista'
    )
    titulo_eleitor = models.CharField(
        max_length=15, 
        blank=True, 
        null=True, 
        verbose_name='Título de Eleitor'
    )
    
    # Campos para anexos
    anexo_cpf = models.FileField(
        upload_to='documentos/cpf/', 
        blank=True, 
        null=True, 
        verbose_name='Anexo CPF'
    )
    anexo_ctps = models.FileField(
        upload_to='documentos/ctps/', 
        blank=True, 
        null=True, 
        verbose_name='Anexo CTPS'
    )
    anexo_pis = models.FileField(
        upload_to='documentos/pis/', 
        blank=True, 
        null=True, 
        verbose_name='Anexo PIS'
    )
    anexo_rg = models.FileField(
        upload_to='documentos/rg/', 
        blank=True, 
        null=True, 
        verbose_name='Anexo RG'
    )

    class Meta:
        db_table = 'documentos'
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['-data_atualizacao']

    def __str__(self):
        return f"{self.nome} - {self.funcionario.nome}"

    def clean(self):
        # Verifica se o documento está sendo definido como principal
        if hasattr(self, 'admissao_vinculada') and self.admissao_vinculada:
            # Verifica se já existe outro documento principal para este funcionário
            if Documentos.objects.filter(
                funcionario=self.funcionario,
                admissao_vinculada__isnull=False
            ).exclude(pk=self.pk).exists():
                raise ValidationError('Já existe um documento principal para este funcionário')
                
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validação condicional baseada no tipo de documento
        if self.tipo == 'CPF' and not self.cpf:
            raise ValidationError({'cpf': 'CPF é obrigatório para este tipo de documento'})
        if self.tipo == 'PIS' and not self.pis:
            raise ValidationError({'pis': 'PIS é obrigatório para este tipo de documento'})
        if self.tipo == 'CTPS' and not self.ctps:
            raise ValidationError({'ctps': 'CTPS é obrigatório para este tipo de documento'})
        if self.tipo == 'RG' and (not self.rg or not self.uf or not self.emissor):
            raise ValidationError({
                'rg': 'RG, UF e Órgão Emissor são obrigatórios para este tipo de documento'
            })
        if self.tipo == 'RES' and not self.reservista:
            raise ValidationError({'reservista': 'Número de reservista é obrigatório para este tipo de documento'})
        if self.tipo == 'TIT' and not self.titulo_eleitor:
            raise ValidationError({'titulo_eleitor': 'Título de eleitor é obrigatório para este tipo de documento'})

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
    
    funcionario = models.OneToOneField(  # Alterado para ser o relacionamento principal
        'Funcionarios',
        on_delete=models.CASCADE,
        related_name='admissao'
    )
    documento_principal = models.OneToOneField(
        Documentos, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admissao_vinculada'
    )
    cargo = models.ForeignKey('Cargos', on_delete=models.PROTECT, related_name='admissoes')
    departamento = models.ForeignKey('Departamentos', on_delete=models.PROTECT, related_name='admissoes')
    matricula = models.CharField(max_length=10, unique=True)
    data_admissao = models.DateField(default=timezone.now)
    salario = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_contrato = models.CharField(max_length=3, choices=TIPO_CONTRATO_CHOICES, default='CLT')
    data_demissao = models.DateField(null=True, blank=True)
    hora_entrada = models.TimeField(verbose_name='Horário de entrada', null=True, blank=True)
    hora_saida = models.TimeField(verbose_name='Horário de saída', null=True, blank=True)
    dias_trabalhado = models.CharField(max_length=27, blank=True)
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



