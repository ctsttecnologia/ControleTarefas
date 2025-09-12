

# models.py

from datetime import date
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.managers import FilialManager
from usuario.models import Filial
from cliente.models import Cliente


class Departamento(models.Model):
    """
    Representa um departamento dentro de uma filial da empresa.
    Ex: Financeiro, Recursos Humanos, TI.
    """
    nome = models.CharField(
        _("Nome do Departamento"),
        max_length=100,
        unique=True
    )
    centro_custo = models.CharField(
        _("Centro de Custo"),
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )
    ativo = models.BooleanField(
        _("Ativo"),
        default=True
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='departamentos',  
        verbose_name=_("Filial"),
        null=True,            
        blank=False          
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()
   

    class Meta:
        verbose_name = _("Departamento")
        verbose_name_plural = _("Departamentos")
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Cargo(models.Model):
    """
    Representa um cargo ou função exercida dentro da empresa.
    Ex: Analista Financeiro, Desenvolvedor Pleno.
    """
    nome = models.CharField(
        _("Nome do Cargo"),
        max_length=100,
        unique=True
    )
    descricao = models.TextField(
        _("Descrição Sumária do Cargo"),
        blank=True
    )
    cbo = models.CharField(
        _("CBO"),
        max_length=10,
        blank=True,
        help_text=_("Classificação Brasileira de Ocupações")
    )
    ativo = models.BooleanField(
        _("Ativo"),
        default=True
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='cargos',  
        verbose_name=_("Filial"),
        null=True,
        blank=False
    )

    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        verbose_name = _("Cargo")
        verbose_name_plural = _("Cargos")
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Funcionario(models.Model):
    """
    Modelo central que representa um colaborador da empresa, unindo
    dados pessoais, de contato e de contratação.
    """
    # Choices para campos com opções fixas
    STATUS_CHOICES = [
        ('ATIVO', _('Ativo')),
        ('INATIVO', _('Inativo')),
        ('FERIAS', _('Férias')),
        ('AFASTADO', _('Afastado'))
    ]
    SEXO_CHOICES = [
        ('M', _('Masculino')),
        ('F', _('Feminino')),
        ('O', _('Outro'))
    ]

    # --- Relacionamentos Fundamentais ---
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='funcionario',
        verbose_name=_("Usuário do Sistema"),
        null=True,
        blank=True,
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='funcionarios',  
        verbose_name=_("Filial de Lotação"),
        null=True,
        blank=False
    )
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.PROTECT,
        related_name='funcionarios',
        verbose_name=_("Cargo")
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='funcionarios',
        verbose_name=_("Departamento")
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL, # Permite remover o cliente sem apagar o funcionário
        related_name='funcionarios_alocados',
        verbose_name=_("Cliente/Contrato"),
        null=True,
        blank=True
    )

    # --- Informações Pessoais ---
    nome_completo = models.CharField(_("Nome Completo"), max_length=255)
    data_nascimento = models.DateField(_("Data de Nascimento"), null=True, blank=True)
    sexo = models.CharField(_("Sexo"), max_length=1, choices=SEXO_CHOICES, null=True, blank=True)
    email_pessoal = models.EmailField(_("Email Pessoal"), unique=True, null=True, blank=True)
    telefone = models.CharField(_("Telefone de Contato"), max_length=20, blank=True)

    # --- Informações de Contratação ---
    matricula = models.CharField(_("Matrícula"), max_length=20, unique=True)
    data_admissao = models.DateField(_("Data de Admissão"))
    data_demissao = models.DateField(_("Data de Demissão"), null=True, blank=True)
    salario = models.DecimalField(_("Salário Base"), max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(_("Status"), max_length=10, choices=STATUS_CHOICES, default='ATIVO')

    # --- Metadados ---
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    foto_3x4 = models.ImageField(
        _("Foto 3x4"),
        upload_to='fotos_3x4/', 
        null=True,
        blank=True,
        help_text=_("Faça o upload de uma foto 3x4 do funcionário.")
    )

    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        db_table = 'departamento_pessoal_funcionario'
        verbose_name = _("Funcionário")
        verbose_name_plural = _("Funcionários")
        ordering = ['nome_completo']

    def __str__(self):
        return self.nome_completo

    def get_absolute_url(self):
        """URL canônica para um funcionário específico."""
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.pk})

    @property
    def idade(self):
        """Calcula a idade do funcionário com base na data de nascimento."""
        if not self.data_nascimento:
            return None
        hoje = date.today()
        # Calcula a diferença de anos e subtrai 1 se o aniversário ainda não ocorreu este ano.
        return hoje.year - self.data_nascimento.year - ((hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day))
    
    # O decorador @property já torna o método acessível como um atributo,
    # então o uso de 'idade.fget.short_description' não é necessário ou é um padrão antigo.
    # O Django Admin pode inferir o nome do campo do próprio nome do método (@property).


class Documento(models.Model):
    """
    Armazena documentos específicos (CPF, RG, etc.) associados a um funcionário.
    """
    TIPO_CHOICES = [
        ('CPF', _('CPF')),
        ('RG', _('RG')),
        ('CTPS', _('CTPS')),
        ('CNH', _('CNH')),
        ('PIS', _('PIS')),
        ('OUTRO', _('Outro'))
    ]

    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,  
        related_name='documentos',
        verbose_name=_("Funcionário")
    )
    tipo = models.CharField(_("Tipo de Documento"), max_length=10, choices=TIPO_CHOICES)
    numero = models.CharField(_("Número/Código do Documento"), max_length=50)
    anexo = models.FileField(
        _("Arquivo Anexado"),
        upload_to='documentos_funcionarios/',
        blank=True,
        null=True
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='documentos_filial', 
        verbose_name=_("Filial"),
        null=True,
        blank=False
    )

    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        verbose_name = _("Documento")
        verbose_name_plural = _("Documentos")
        # Garante que um funcionário só pode ter um documento de cada tipo.
        unique_together = ('funcionario', 'tipo')

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.funcionario.nome_completo}"
