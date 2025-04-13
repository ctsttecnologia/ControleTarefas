from django.db import models
from django.utils import timezone
from .constant import ESTADOS_BRASIL
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class Logradouro(models.Model):
    # Validadores
    cep_validator = RegexValidator(
        regex=r'^\d{8}$',
        message=_('CEP deve conter exatamente 8 dígitos')
    )
    
    numero_validator = MinValueValidator(
        1,
        message=_('Número não pode ser menor que 1')
    )
    
    # Campos do modelo
    endereco = models.CharField(
        max_length=150,
        verbose_name=_('Endereço'),
        help_text=_('Nome da rua, avenida, etc.')
    )
    
    numero = models.IntegerField(
        validators=[numero_validator],
        verbose_name=_('Número')
    )
    
    cep = models.CharField(
        max_length=8,
        validators=[cep_validator],
        verbose_name=_('CEP'),
        help_text=_('Apenas números (8 dígitos)')
    )
    
    complemento = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('Complemento')
    )
    
    bairro = models.CharField(
        max_length=60,
        verbose_name=_('Bairro')
    )
    
    cidade = models.CharField(
        max_length=60,
        verbose_name=_('Cidade')
    )
    
    estado = models.CharField(
        max_length=2,
        choices=ESTADOS_BRASIL,
        default='SP',
        verbose_name=_('Estado')
    )
    
    pais = models.CharField(
        max_length=30,
        default='Brasil',
        verbose_name=_('País')
    )
    
    ponto_referencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Ponto de Referência')
    )
    
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_('Latitude')
    )
    
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_('Longitude')
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
        
        # Validação do estado com a cidade
        if self.estado == 'SP' and 'São Paulo' not in self.cidade:
            raise ValidationError({
                'cidade': _('Cidades de SP devem conter "São Paulo" no nome')
            })
    
    def save(self, *args, **kwargs):
        """Garante validações antes de salvar"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def cep_formatado(self):
        """Retorna CEP formatado"""
        return f"{self.cep[:5]}-{self.cep[5:]}" if self.cep else ""
    
    @property
    def coordenadas(self):
        """Retorna coordenadas formatadas"""
        if self.latitude and self.longitude:
            return f"{self.latitude}, {self.longitude}"
        return _("Não informado")
    
    def get_endereco_completo(self):
        """Retorna o endereço completo formatado"""
        complemento = f", {self.complemento}" if self.complemento else ""
        return (
            f"{self.endereco}, {self.numero}{complemento} - "
            f"{self.bairro}, {self.cidade}/{self.estado} - "
            f"{self.cep_formatado}"
        )
    
    def __str__(self):
        return self.get_endereco_completo()
    
    class Meta:
        db_table = 'logradouro'
        verbose_name = _('Logradouro')
        verbose_name_plural = _('Logradouros')
        ordering = ['estado', 'cidade', 'bairro', 'endereco']
        indexes = [
            models.Index(fields=['estado', 'cidade'], name='idx_estado_cidade'),
            models.Index(fields=['cep'], name='idx_logradouro_cep'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['endereco', 'numero', 'complemento', 'cep'],
                name='unique_endereco_completo'
            ),
        ]
