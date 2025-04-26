
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone

from logradouro.models import Logradouro

class Cliente(models.Model):
    # Validador de CNPJ
    cnpj_validator = RegexValidator(
        regex=r'^\d{14}$',
        message=_('CNPJ deve conter exatamente 14 dígitos numéricos')
    )
    
    # Validador de telefone
    telefone_validator = RegexValidator(
        regex=r'^\d{10,11}$',
        message=_('Telefone deve conter 10 ou 11 dígitos (DDD + número)')
    )
    
    # Campos do modelo
    nome = models.CharField(
        max_length=100,
        verbose_name=_('Nome Fantasia'),
        help_text=_('Nome comercial do cliente')
    )
    
    logradouro = models.ForeignKey(
        Logradouro,
        on_delete=models.PROTECT,
        related_name='clientes',
        verbose_name=_('Endereço')
    )
    
    contrato = models.CharField(
        max_length=4,
        default='0000',
        verbose_name=_('Número do Contrato'),
        help_text=_('Código de 4 dígitos do contrato')
    )
    
    razao_social = models.CharField(
        max_length=100,
        verbose_name=_('Razão Social'),
        help_text=_('Nome legal da empresa')
    )
    
    unidade = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Unidade/Filial'),
        help_text=_('Número da unidade/filial, se aplicável')
    )
    
    cnpj = models.CharField(
        max_length=14,
        default='00000000000000',
        validators=[cnpj_validator],
        unique=True,
        verbose_name=_('CNPJ'),
        help_text=_('14 dígitos do Cadastro Nacional de Pessoa Jurídica')
    )
    
    telefone = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        validators=[telefone_validator],
        verbose_name=_('Telefone'),
        help_text=_('Número com DDD (10 ou 11 dígitos)')
    )
    
    data_de_inicio = models.DateField(
        verbose_name=_('Data de Início'),
        help_text=_('Data de início do contrato')
    )
    
    estatus = models.BooleanField(
        default=True,
        verbose_name=_('Ativo?'),
        help_text=_('Indica se o cliente está ativo')
    )
    
    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Data de Cadastro')
    )
    
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Atualização')
    )
    
    # Métodos avançados
    def clean(self):
        """Validações personalizadas"""
        super().clean()
        
        # Validação da data de início
        if self.data_de_inicio and self.data_de_inicio > timezone.now().date():
            raise ValidationError({
                'data_de_inicio': _('A data de início não pode ser no futuro.')
            })
        
        # Validação do CNPJ padrão
        if self.cnpj == '00000000000000':
            raise ValidationError({
                'cnpj': _('Por favor, informe um CNPJ válido.')
            })
    
    def save(self, *args, **kwargs):
        """Garante validações antes de salvar"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def tempo_contrato(self):
        """Retorna o tempo de contrato em meses"""
        if self.data_de_inicio:
            delta = timezone.now().date() - self.data_de_inicio
            return round(delta.days / 30)
        return 0
    
    @property
    def nome_completo(self):
        """Retorna nome fantasia + razão social"""
        return f"{self.nome} ({self.razao_social})"
    
    @property
    def cnpj_formatado(self):
        """Retorna CNPJ formatado"""
        if len(self.cnpj) == 14:
            return f"{self.cnpj[:2]}.{self.cnpj[2:5]}.{self.cnpj[5:8]}/{self.cnpj[8:12]}-{self.cnpj[12:]}"
        return self.cnpj
    
    def ativar(self):
        """Ativa o cliente"""
        self.estatus = True
        self.save()
    
    def desativar(self):
        """Desativa o cliente"""
        self.estatus = False
        self.save()
    
    def __str__(self):
        return self.nome_completo
    
    class Meta:
        db_table = 'cliente'
        verbose_name = _('Cliente')
        verbose_name_plural = _('Clientes')
        ordering = ['nome']
        indexes = [
            models.Index(fields=['cnpj'], name='idx_cliente_cnpj'),
            models.Index(fields=['estatus'], name='idx_cliente_status'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['cnpj'],
                name='unique_cliente_cnpj'
            ),
            models.CheckConstraint(
                check=models.Q(data_de_inicio__lte=timezone.now().date()),
                name='check_data_inicio_passado'
            ),
        ]

class ClienteCliente(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='unidades_cliente',
        verbose_name=_('Cliente Matriz')
    )
    
    nome = models.CharField(
        max_length=100,
        verbose_name=_('Nome da Unidade'),
        help_text=_('Nome ou identificação da unidade/filial')
    )
    
    codigo = models.CharField(
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_('Código da Unidade'),
        help_text=_('Código interno da unidade')
    )
    
    ativa = models.BooleanField(
        default=True,
        verbose_name=_('Ativa?')
    )
    
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Data de Criação')
    )
    
    # Métodos avançados
    @property
    def nome_completo(self):
        """Retorna nome da unidade com cliente"""
        return f"{self.nome} ({self.cliente.nome})"
    
    def __str__(self):
        return self.nome_completo
    
    class Meta:
        db_table = 'cliente_cliente'
        verbose_name = _('Unidade do Cliente')
        verbose_name_plural = _('Unidades dos Clientes')
        ordering = ['cliente', 'nome']
        indexes = [
            models.Index(fields=['cliente'], name='idx_clientecliente_cliente'),
        ]

class Logradouro(models.Model):
    
    def cep_formatado(self):
        if self.cep and len(self.cep) == 8:
            return f"{self.cep[:5]}-{self.cep[5:]}"
        return self.cep