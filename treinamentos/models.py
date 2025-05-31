from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User


class TipoTreinamento(models.Model):
    MODALIDADE_CHOICES = [
        ('I', _('Interno')),
        ('E', _('Externo')),
        ('H', _('Híbrido')),
        ('O', _('Online')),
    ]
    
    AREA_CHOICES = [
        ('TEC', _('Tecnologia')),
        ('ADM', _('Administrativo')),
        ('OPR', _('Operacional')),
        ('SEG', _('Segurança')),
        ('SAU', _('Saúde')),
        ('OUT', _('Outros')),
    ]
    
    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Nome do Tipo'),
        help_text=_('Nome descritivo do tipo de treinamento')
    )
    
    modalidade = models.CharField(
        max_length=1,
        choices=MODALIDADE_CHOICES,
        verbose_name=_('Modalidade'),
        help_text=_('Forma de realização do treinamento')
    )
    
    area = models.CharField(
        max_length=3,
        choices=AREA_CHOICES,
        default='OUT',
        verbose_name=_('Área de Conhecimento')
    )
    
    descricao = models.TextField(
        verbose_name=_('Descrição'),
        blank=True,
        null=True,
        help_text=_('Detalhes sobre este tipo de treinamento')
    )
    
    certificado = models.BooleanField(
        default=True,
        verbose_name=_('Emite Certificado?')
    )
    
    validade_meses = models.PositiveIntegerField(
        default=12,
        verbose_name=_('Validade em Meses'),
        help_text=_('Validade padrão do treinamento em meses')
    )
    
    ativo = models.BooleanField(
        default=True,
        verbose_name=_('Ativo?')
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
    @property
    def modalidade_formatada(self):
        """Retorna a modalidade formatada"""
        return dict(self.MODALIDADE_CHOICES).get(self.modalidade, self.modalidade)
    
    @property
    def area_formatada(self):
        """Retorna a área formatada"""
        return dict(self.AREA_CHOICES).get(self.area, self.area)
    
    def __str__(self):
        return f"{self.nome} ({self.modalidade_formatada})"
    
    class Meta:
        verbose_name = _('Tipo de Treinamento')
        verbose_name_plural = _('Tipos de Treinamento')
        ordering = ['nome']
        indexes = [
            models.Index(fields=['nome'], name='idx_tipo_treinamento_nome'),
            models.Index(fields=['modalidade'], name='idx_tipo_treina_modalidade'),
            models.Index(fields=['area'], name='idx_tipo_treinamento_area'),
        ]

class Treinamento(models.Model):

    MODALIDADE_CHOICES = [
        ('interno', 'Interno'),
        ('externo', 'Externo'),
    ]
    
    TIPO_CHOICES = [
        ('graduacao', 'Graduação'),
        ('tecnico', 'Técnico'),
        ('profissionalizante', 'Profissionalizante'),
        ('livre', 'Livre'),
        ('outros', 'Outros'),
    ]
    
    STATUS_CHOICES = [
        ('P', _('Planejado')),
        ('A', _('Agendado')),
        ('E', _('Em Andamento')),
        ('C', _('Concluído')),
        ('X', _('Cancelado')),
    ]
    
    tipo_treinamento = models.ForeignKey(
        TipoTreinamento,
        on_delete=models.PROTECT,
        related_name='treinamentos',
        verbose_name=_('Tipo de Treinamento')
    )
    
    nome = models.CharField(
        max_length=200,
        verbose_name=_('Nome do Treinamento'),
        help_text=_('Nome completo do treinamento')
    )
    
    data_inicio = models.DateTimeField(
       default=timezone.now
    )
    
    data_vencimento = models.DateField(
        verbose_name=_('Data de Vencimento'),
        help_text=_('Data de validade do treinamento')
    )
    
    duracao = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Duração (horas)'),
        null=True, blank=True,
        help_text=_('Duração total em horas')
    )
    
    atividade = models.CharField(
        max_length=200,
        verbose_name=_('Atividade Relacionada'),
        help_text=_('Atividade ou processo relacionado')
    )
    
    descricao = models.TextField(
        verbose_name=_('Descrição Detalhada'),
        blank=True,
        null=True
    )
    
    funcionario = models.CharField(
        max_length=100,
        verbose_name=_('Responsável'),
        help_text=_('Funcionário responsável pela organização')
    )
    
    cm = models.CharField(
        max_length=100,
        verbose_name=_('Coordenador/Mentor'),
        help_text=_('Coordenador ou mentor do treinamento')
    )
    
    palestrante = models.CharField(
        max_length=100,
        verbose_name=_('Palestrante/Instrutor'),
        help_text=_('Nome do palestrante ou instrutor')
    )
    
    hxh = models.IntegerField(default=0,
        verbose_name=_('Horas por Participante'),
        help_text=_('Horas necessárias por participante')
    )
    
    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        default='P',
        verbose_name=_('Status')
    )
    
    local = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('Local do Treinamento')
    )
    
    custo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Custo Estimado')
    )
    
    participantes_previstos = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Participantes Previstos')
    )
    
    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Data de Cadastro')
    )
    
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Atualização')
    )

    def __str__(self):
        return self.nome  # Corrigido para retornar o nome

    # método para facilitar
    @property
    def tipo_display(self):
        return dict(self.TIPO_CHOICES).get(self.tipo, self.tipo)

    # Métodos avançados
    def clean(self):
        """Validações personalizadas"""
        super().clean()
        
        # Validação de datas
        if self.data_vencimento and self.data_inicio:
            if self.data_vencimento < self.data_inicio.date():
                raise ValidationError({
                    'data_vencimento': _('Data de vencimento não pode ser anterior à data de início')
                })
        
        # Validação de horas
        if self.hxh > self.duracao:
            raise ValidationError({
                'hxh': _('Horas por participante não podem ser maiores que a duração total')
            })
    
    def save(self, *args, **kwargs):
        """Lógica adicional ao salvar"""
        # Calcula data de vencimento se não informada
        if not self.data_vencimento and self.tipo_treinamento:
            self.data_vencimento = self.data_inicio.date() + timedelta(
                days=30 * self.tipo_treinamento.validade_meses
            )
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def status_formatado(self):
        """Retorna status formatado"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    @property
    def tempo_restante(self):
        """Calcula dias restantes para início"""
        if self.data_inicio > timezone.now():
            delta = self.data_inicio - timezone.now()
            return delta.days
        return 0
    
    @property
    def custo_total_estimado(self):
        """Calcula custo total estimado"""
        return self.custo * self.participantes_previstos
    
    @property
    def carga_horaria_total(self):
        """Calcula a carga horária total do treinamento"""
        if self.duracao is None or self.Hxh is None:
            return 0
        return self.duracao * self.Hxh

       
    class Meta:
        
        verbose_name = _('Treinamento')
        verbose_name_plural = _('Treinamentos')
        ordering = ['-data_inicio']
        indexes = [
            models.Index(fields=['tipo_treinamento'], name='idx_treinamento_tipo'),
            models.Index(fields=['data_inicio'], name='idx_treinamento_data'),
            models.Index(fields=['status'], name='idx_treinamento_status'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(data_vencimento__gte=models.F('data_inicio')),
                name='check_data_vencimento_maior_inicio'
            ),
            models.CheckConstraint(
                check=models.Q(hxh__lte=models.F('duracao')),
                name='check_hxh_menor_duracao'
            ),
        ]

from django.db import models

class TreinamentoDisponivel(models.Model):
    MODALIDADE_CHOICES = [
        ('interno', 'Interno'),
        ('externo', 'Externo'),
    ]
    
    TIPO_CHOICES = [
        ('graduacao', 'Graduação'),
        ('tecnico', 'Técnico'),
        ('profissionalizante', 'Profissionalizante'),
        ('livre', 'Livre'),
        ('outros', 'Outros'),
    ]

    codigo = models.CharField('Código', max_length=20, unique=True)
    nome = models.CharField('Nome do Treinamento', max_length=100)
    descricao = models.TextField('Descrição', blank=True)
    carga_horaria = models.PositiveIntegerField('Carga Horária (horas)')
    validade_meses = models.PositiveIntegerField('Validade (meses)')
    modalidade = models.CharField('Modalidade', max_length=10, choices=MODALIDADE_CHOICES)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    fornecedor = models.CharField('Fornecedor', max_length=100, blank=True)
    custo = models.DecimalField('Custo', max_digits=10, decimal_places=2, null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Treinamento'
        verbose_name_plural = 'Treinamentos'
        ordering = ['nome']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    def get_absolute_url(self):
        return reverse('treinamento_detail', args=[str(self.id)])

from django.contrib.auth.models import User

class Colaborador(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    matricula = models.CharField(max_length=20, unique=True)
    departamento = models.CharField(max_length=100)
    cargo = models.CharField(max_length=100)
    data_admissao = models.DateField()
    ativo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.matricula})"

class TreinamentoColaborador(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('expirado', 'Expirado'),
        ('proximo', 'Próximo a vencer'),
    ]
    
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='treinamentos')
    treinamento = models.ForeignKey(Treinamento, on_delete=models.CASCADE)
    data_realizacao = models.DateField()
    data_validade = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    certificado = models.FileField(upload_to='certificados/', null=True, blank=True)
    
    class Meta:
        unique_together = ('colaborador', 'treinamento')
    
    @property
    def dias_para_vencer(self):
        return (self.data_validade - timezone.now().date()).days
    
    def save(self, *args, **kwargs):
        # Atualiza status automaticamente
        if self.data_validade < timezone.now().date():
            self.status = 'expirado'
        elif self.dias_para_vencer <= 30:
            self.status = 'proximo'
        else:
            self.status = 'ativo'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.colaborador} - {self.treinamento}"

        