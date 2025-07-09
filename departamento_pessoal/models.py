
# departamento_pessoal/models.py (VERSÃO FINAL REFAORADA)

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import date

# --- Modelos de Apoio / Catálogos ---

class Departamento(models.Model):
    """ Tabela para os departamentos da empresa. """
    nome = models.CharField(max_length=100, unique=True, verbose_name=_("Nome do Departamento"))
    centro_custo = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name=_("Centro de Custo"))
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Departamento")
        verbose_name_plural = _("Departamentos")
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Cargo(models.Model):
    """ Tabela para os cargos da empresa. """
    nome = models.CharField(max_length=100, unique=True, verbose_name=_("Nome do Cargo"))
    descricao = models.TextField(blank=True, verbose_name=_("Descrição Sumária do Cargo"))
    cbo = models.CharField(max_length=10, blank=True, verbose_name=_("CBO"))
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Cargo")
        verbose_name_plural = _("Cargos")
        ordering = ['nome']

    def __str__(self):
        return self.nome


# --- Modelo Central de Funcionário ---

class Funcionario(models.Model):
    """ 
    Modelo unificado que representa um funcionário, seus dados pessoais e de contratação.
    Este modelo agora contém os campos que antes estavam em Admissao.
    """
    STATUS_CHOICES = [('ATIVO', 'Ativo'), ('INATIVO', 'Inativo'), ('FERIAS', 'Férias'), ('AFASTADO', 'Afastado')]
    SEXO_CHOICES = [('M', 'Masculino'), ('F', 'Feminino'), ('O', 'Outro')]

    # Relação com o sistema de autenticação do Django
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        related_name='funcionario',
        verbose_name=_("Usuário do Sistema")
    )
    
    # Informações Pessoais
    nome_completo = models.CharField(max_length=255, verbose_name=_("Nome Completo"))
    data_nascimento = models.DateField(null=True, blank=True, verbose_name=_("Data de Nascimento"))
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, null=True, blank=True)
    
    # Contato
    email_pessoal = models.EmailField(unique=True, null=True, blank=True, verbose_name=_("Email Pessoal"))
    telefone = models.CharField(max_length=20, blank=True, verbose_name=_("Telefone de Contato"))

    # Informações de Contratação (antes em Admissao)
    matricula = models.CharField(max_length=20, unique=True, verbose_name=_("Matrícula"))
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name='funcionario', verbose_name=_("Cargo"))
    departamento = models.ForeignKey(Departamento, on_delete=models.PROTECT, related_name='funcionario', verbose_name=_("Departamento"))
    data_admissao = models.DateField(verbose_name=_("Data de Admissão"))
    data_demissao = models.DateField(null=True, blank=True, verbose_name=_("Data de Demissão"))
    salario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Salário Base"))
    
    # Status do Funcionário
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ATIVO')

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = ('departamento_pessoal_funcionario')
        verbose_name = _("Funcionário")
        verbose_name_plural = _("Funcionários")
        ordering = ['nome_completo']

    def __str__(self):
        return self.nome_completo

    def get_absolute_url(self):
        return reverse('departamento_pessoal:funcionario_detail', kwargs={'pk': self.pk})

    @property
    def idade(self):
        if not self.data_nascimento:
            return None
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - ((hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day))

class Documento(models.Model):
    """ Documentos específicos associados a um funcionário. """
    TIPO_CHOICES = [('CPF', 'CPF'), ('RG', 'RG'), ('CTPS', 'CTPS'), ('OUTRO', 'Outro')]
    
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='documentos')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    numero = models.CharField(max_length=50, verbose_name=_("Número/Código do Documento"))
    anexo = models.FileField(upload_to='documentos_funcionario/', blank=True, null=True)

    class Meta:
        unique_together = ('funcionario', 'tipo')

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.funcionario.nome_completo}"
    


