
from django.db import models
from django.core.validators import RegexValidator, EmailValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone

from logradouro.models import Logradouro

class Cliente(models.Model):
    # Validador de CNPJ corrigido
    cnpj_validator = RegexValidator(
        regex=r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$|^\d{14}$',
        message=_('CNPJ deve estar no formato 00.000.000/0000-00 ou conter 14 dígitos')
    )
    
    # Validador de telefone corrigido
    telefone_validator = RegexValidator(
        regex=r'^\(\d{2}\) \d{4,5}-\d{4}$|^\d{10,11}$',
        message=_('Telefone deve estar no formato (00) 00000-0000 ou conter 10/11 dígitos')
    )
    
    # Validador de email
    email_validator = EmailValidator(
        message=_('Informe um endereço de email válido')
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
        verbose_name=_('Número do Contrato (CM)'),
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
        max_length=18,  # Tamanho para formato com pontuação
        unique=True,
        verbose_name=_('CNPJ'),
        help_text=_('Formato: 00.000.000/0000-00'),
        validators=[cnpj_validator]
    )
    
    telefone = models.CharField(
        max_length=15,  # Tamanho para formato com parênteses e traço
        null=True,
        blank=True,
        verbose_name=_('Telefone'),
        help_text=_('Formato: (00) 00000-0000'),
        validators=[telefone_validator]
    )
    
    email = models.EmailField(
        max_length=100,
        null=True,
        blank=True,
        validators=[email_validator],
        verbose_name=_('E-mail'),
        help_text=_('Endereço de e-mail para contato')
    )
    
    observacoes = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Observações'),
        help_text=_('Informações adicionais sobre o cliente')
    )
    
    inscricao_estadual = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_('Inscrição Estadual'),
        help_text=_('Número de inscrição estadual')
    )
    
    inscricao_municipal = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_('Inscrição Municipal'),
        help_text=_('Número de inscrição municipal')
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

    data_encerramento = models.DateField(
        null=True, 
        blank=True, 
        verbose_name=_('Data de Encerramento')
    )
    
    # Métodos avançados
    def clean(self):
        """Validações personalizadas"""
        super().clean()

        # Remove formatação para validação
        cnpj_limpo = ''.join(filter(str.isdigit, self.cnpj))
        telefone_limpo = ''.join(filter(str.isdigit, self.telefone)) if self.telefone else None
        
        # Validação da data de início
        if self.data_de_inicio and self.data_de_inicio > timezone.now().date():
            raise ValidationError({
                'data_de_inicio': _('A data de início não pode ser no futuro.')
            })
        
        # Validação do CNPJ
        if len(cnpj_limpo) != 14:
            raise ValidationError({
                'cnpj': _('CNPJ deve conter exatamente 14 dígitos.')
            })
        
        # Validação do telefone
        if telefone_limpo and len(telefone_limpo) not in [10, 11]:
            raise ValidationError({
                'telefone': _('Telefone deve conter 10 ou 11 dígitos (com DDD).')
            })
    
    def save(self, *args, **kwargs):
        """Garante validações antes de salvar"""
        self.full_clean()
        super().save(*args, **kwargs)
    
        # Formata o CNPJ antes de salvar
        cnpj_limpo = ''.join(filter(str.isdigit, self.cnpj))
        if len(cnpj_limpo) == 14:
            self.cnpj = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
        
        # Formata o telefone antes de salvar
        if self.telefone:
            tel_limpo = ''.join(filter(str.isdigit, self.telefone))
            if len(tel_limpo) == 11:
                self.telefone = f"({tel_limpo[:2]}) {tel_limpo[2:7]}-{tel_limpo[7:]}"
            elif len(tel_limpo) == 10:
                self.telefone = f"({tel_limpo[:2]}) {tel_limpo[2:6]}-{tel_limpo[6:]}"
        
        super().save(*args, **kwargs)
    
    @property
    def cnpj_formatado(self):
        """Retorna CNPJ formatado consistentemente"""
        cnpj_limpo = ''.join(filter(str.isdigit, self.cnpj))
        if len(cnpj_limpo) == 14:
            return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
        return self.cnpj

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
    

    