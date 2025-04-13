from django.db import models
from django.utils import timezone
from epi.models import FichaEPI
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class EquipamentosSeguranca(models.Model):
    TIPO_EQUIPAMENTO_CHOICES = [
        ('EPI', 'Equipamento de Proteção Individual'),
        ('EPC', 'Equipamento de Proteção Coletiva'),
        ('INC', 'Incêndio'),
        ('SOC', 'Socorro'),
        ('OUT', 'Outros'),
    ]
    
    STATUS_CHOICES = [
        (1, 'Ativo'),
        (0, 'Inativo'),
    ]
    
    # Validadores
    codigo_ca_validator = RegexValidator(
        regex=r'^[A-Z]{2}-\d{4}$',
        message=_('Formato do CA deve ser AA-1234')
    )
    
    # Campos do modelo
    nome_equipamento = models.CharField(
        max_length=100,
        verbose_name=_('Nome do Equipamento'),
        help_text=_('Nome completo do equipamento')
    )
    
    tipo = models.CharField(
        max_length=3,
        choices=TIPO_EQUIPAMENTO_CHOICES,
        default='EPI',
        verbose_name=_('Tipo de Equipamento')
    )
    
    codigo_ca = models.CharField(
        db_column='codigo_CA',
        max_length=10,
        unique=True,
        validators=[codigo_ca_validator],
        verbose_name=_('Código CA'),
        help_text=_('Código de aprovação no formato AA-1234')
    )
    
    descricao = models.TextField(
        verbose_name=_('Descrição'),
        help_text=_('Descrição detalhada do equipamento')
    )
    
    quantidade_estoque = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Quantidade em Estoque'),
        validators=[MinValueValidator(0)]
    )
    
    estoque_minimo = models.PositiveIntegerField(
        default=5,
        verbose_name=_('Estoque Mínimo'),
        help_text=_('Quantidade mínima para alerta de reposição')
    )
    
    data_validade = models.DateField(
        verbose_name=_('Data de Validade'),
        help_text=_('Validade do certificado de aprovação'),
        null=True,
        blank=True
    )
    
    ativo = models.IntegerField(
        choices=STATUS_CHOICES,
        default=1,
        verbose_name=_('Status')
    )
    
    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Data de Cadastro')
    )
    
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Atualização')
    )
    
    # Relacionamento com FichaEPI
    fichas_epi = models.ManyToManyField(
        FichaEPI,
        through='ItemEquipamentoSeguranca',
        related_name='equipamentos',
        verbose_name=_('Fichas EPI Associadas')
    )

    # Métodos avançados
    def clean(self):
        """Validações personalizadas"""
        super().clean()
        
        # Valida data de validade
        if self.data_validade and self.data_validade < timezone.now().date():
            raise ValidationError({
                'data_validade': _('Data de validade não pode ser no passado')
            })
        
        # Valida estoque mínimo
        if self.estoque_minimo < 1:
            raise ValidationError({
                'estoque_minimo': _('Estoque mínimo deve ser pelo menos 1')
            })
    
    def save(self, *args, **kwargs):
        """Garante validações antes de salvar"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def precisa_repor(self):
        """Verifica se precisa repor estoque"""
        return self.quantidade_estoque < self.estoque_minimo
    
    @property
    def status_formatado(self):
        """Retorna status formatado"""
        return dict(self.STATUS_CHOICES).get(self.ativo, _('Desconhecido'))
    
    @property
    def tipo_formatado(self):
        """Retorna tipo formatado"""
        return dict(self.TIPO_EQUIPAMENTO_CHOICES).get(self.tipo, self.tipo)
    
    def __str__(self):
        return f"{self.nome_equipamento} ({self.codigo_ca})"
    
    class Meta:
        db_table = 'equipamentos_seguranca'
        verbose_name = _('Equipamento de Segurança')
        verbose_name_plural = _('Equipamentos de Segurança')
        ordering = ['tipo', 'nome_equipamento']
        indexes = [
            models.Index(fields=['tipo'], name='idx_tipo_equipamento'),
            models.Index(fields=['codigo_ca'], name='idx_codigo_ca'),
            models.Index(fields=['ativo'], name='idx_status_equipamento'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantidade_estoque__gte=0),
                name='check_quantidade_estoque_positiva'
            ),
            models.CheckConstraint(
                check=models.Q(estoque_minimo__gte=1),
                name='check_estoque_minimo_positivo'
            ),
        ]


class ItemEquipamentoSeguranca(models.Model):
    ficha = models.ForeignKey(
        FichaEPI,
        on_delete=models.CASCADE,
        verbose_name=_('Ficha EPI')
    )
    
    equipamento = models.ForeignKey(
        EquipamentosSeguranca,
        on_delete=models.CASCADE,
        verbose_name=_('Equipamento')
    )
    
    quantidade = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Quantidade'),
        validators=[MinValueValidator(1)]
    )
    
    data_entrega = models.DateField(
        verbose_name=_('Data de Entrega'),
        default=timezone.now
    )
    
    data_devolucao = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Data de Devolução')
    )
    
    responsavel_entrega = models.CharField(
        max_length=100,
        verbose_name=_('Responsável pela Entrega')
    )
    
    observacoes = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Observações')
    )
    
    class Meta:
        db_table = 'itens_equipamento_seguranca'
        verbose_name = _('Item de Equipamento de Segurança')
        verbose_name_plural = _('Itens de Equipamentos de Segurança')
        unique_together = ('ficha', 'equipamento')


