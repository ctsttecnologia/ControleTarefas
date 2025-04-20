# automovel/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from datetime import timedelta

class Carro(models.Model):
    placa_validator = RegexValidator(
        regex=r'^[A-Z]{3}\d{1}[A-Z]{1}\d{2}$|^[A-Z]{3}\d{4}$',
        message=_('Formato de placa inválido. Use AAA1A11 ou AAA1111')
    )
    
    placa = models.CharField(
        max_length=10,
        validators=[placa_validator],
        unique=True,
        verbose_name=_('Placa do Veículo'),
        help_text=_('Formato: AAA1A11 ou AAA1111')
    )
    
    modelo = models.CharField(max_length=50, verbose_name=_('Modelo do Veículo'))
    marca = models.CharField(max_length=50, verbose_name=_('Marca do Veículo'))
    cor = models.CharField(max_length=30, verbose_name=_('Cor do Veículo'))
    
    ano = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1900, message=_('Ano mínimo permitido é 1900')),
            MaxValueValidator(timezone.now().year + 1, message=_('Ano não pode ser no futuro'))
        ],
        verbose_name=_('Ano de Fabricação')
    )
    
    renavan = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Número do RENAVAM'),
        help_text=_('Número único do Registro Nacional de Veículos')
    )
    
    data_ultima_manutencao = models.DateField(
        verbose_name=_('Data da Última Manutenção'),
        null=True,
        blank=True
    )
    
    data_proxima_manutencao = models.DateField(
        verbose_name=_('Data da Próxima Manutenção'),
        null=True,
        blank=True
    )
    
    ativo = models.BooleanField(default=True, verbose_name=_('Veículo Ativo na Frota'))
    observacoes = models.TextField(blank=True, null=True, verbose_name=_('Observações'))

    
    def clean(self):
        super().clean()
        
        if self.data_ultima_manutencao and self.data_proxima_manutencao:
            if self.data_proxima_manutencao <= self.data_ultima_manutencao:
                raise ValidationError({
                    'data_proxima_manutencao': _('A data da próxima manutenção deve ser após a última manutenção.')
                })

    def save(self, *args, **kwargs):
        self.placa = self.placa.upper()
        self.full_clean()
        super().save(*args, **kwargs)

    def calcular_proxima_manutencao(self, dias=90):
        if self.data_ultima_manutencao:
            self.data_proxima_manutencao = self.data_ultima_manutencao + timedelta(days=dias)
            self.save()

    def verificar_manutencao_pendente(self):
        if self.data_proxima_manutencao:
            return self.data_proxima_manutencao <= timezone.now().date()
        return False

    @property
    def idade(self):
        return timezone.now().year - self.ano

    @property
    def status(self):
        if not self.ativo:
            return _('Inativo')
        if self.verificar_manutencao_pendente():
            return _('Ativo - Manutenção Pendente')
        return _('Ativo')

    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placa} ({self.ano})"

    class Meta:
        verbose_name = _('Veículo')
        verbose_name_plural = _('Veículos')
        ordering = ['marca', 'modelo']
        indexes = [
            models.Index(fields=['placa'], name='idx_carro_placa'),
            models.Index(fields=['marca', 'modelo'], name='idx_carro_marca_modelo'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['placa', 'renavan'], name='unique_placa_renavan'),
        ]


class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('agendado', _('Agendado')),
        ('em_andamento', _('Em Andamento')),
        ('concluido', _('Concluído')),
        ('cancelado', _('Cancelado')),
    ]
    
    carro = models.ForeignKey(
        Carro,
        on_delete=models.PROTECT,
        related_name='agendamentos',
        verbose_name=_('Veículo')
    )
    
    funcionario = models.CharField(max_length=100, verbose_name=_('Funcionário Responsável'))
    data_hora_agenda = models.DateTimeField(verbose_name=_('Data/Hora do Agendamento'))
    data_hora_devolucao = models.DateTimeField(
        verbose_name=_('Data/Hora da Devolução'),
        null=True,
        blank=True
    )
    
    cm = models.CharField(max_length=20, verbose_name=_('Código da Missão (CM)'))
    descricao = models.TextField(blank=True, verbose_name=_('Descrição do Agendamento'))
    pedagio = models.BooleanField(default=False, verbose_name=_('Pedágio Necessário?'))
    abastecimento = models.BooleanField(
        default=False,
        verbose_name='Abastecimento Necessário?'
    )
    km_inicial = models.PositiveIntegerField(verbose_name=_('Quilometragem Inicial'))
    km_final = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('Quilometragem Final')
    )
    
    foto_principal = models.ImageField(
        upload_to='agendamentos/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name=_('Foto Principal do Veículo'),
        help_text=_('Foto agendamento')
    )

    class Meta:
        verbose_name = _('Agendamento')
        verbose_name_plural = _('Agendamentos')

    def __str__(self):
        return f"Agendamento #{self.id} - {self.veiculo.placa}"
       
    assinatura = models.TextField(blank=True, verbose_name=_('Assinatura Digital'))
    responsavel = models.CharField(max_length=100, verbose_name=_('Responsável pelo Agendamento'))
    ocorrencia = models.TextField(blank=True, verbose_name=_('Ocorrências Durante o Uso'))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='agendado',
        verbose_name=_('Status do Agendamento')
    )
    
    cancelar_agenda = models.BooleanField(default=False, verbose_name=_('Cancelar Agendamento?'))
    motivo_cancelamento = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Motivo do Cancelamento')
    )

    def clean(self):
        super().clean()
        
        if self.data_hora_devolucao and self.data_hora_agenda:
            if self.data_hora_devolucao <= self.data_hora_agenda:
                raise ValidationError({
                    'data_hora_devolucao': _('A data de devolução deve ser após a data de agendamento.')
                })
        
        if self.km_final and self.km_inicial:
            if self.km_final < self.km_inicial:
                raise ValidationError({
                    'km_final': _('A quilometragem final não pode ser menor que a inicial.')
                })
        
        if (self.cancelar_agenda or self.status == 'cancelado') and not self.motivo_cancelamento:
            raise ValidationError({
                'motivo_cancelamento': _('Motivo do cancelamento é obrigatório quando o agendamento é cancelado.')
            })

    def save(self, *args, **kwargs):
        if self.cancelar_agenda:
            self.status = 'cancelado'
        
        if self.data_hora_devolucao and not self.cancelar_agenda:
            self.status = 'concluido'
        
        self.full_clean()
        super().save(*args, **kwargs)

    def calcular_quilometragem_percorrida(self):
        if self.km_final and self.km_inicial:
            return self.km_final - self.km_inicial
        return None

    def duracao_agendamento(self):
        if self.data_hora_devolucao:
            return self.data_hora_devolucao - self.data_hora_agenda
        return None

    @property
    def necessita_abastecimento(self):
        return self.abastecimento

    @property
    def necessita_pedagio(self):
        return self.pedagio

    def finalizar_agendamento(self, km_final, ocorrencia=None):
        self.km_final = km_final
        self.ocorrencia = ocorrencia or self.ocorrencia
        self.data_hora_devolucao = timezone.now()
        self.save()

    def __str__(self):
        return f"Agendamento {self.id} - {self.carro.placa} ({self.data_hora_agenda})"

    class Meta:
        verbose_name = _('Agendamento de Veículo')
        verbose_name_plural = _('Agendamentos de Veículos')
        ordering = ['-data_hora_agenda']
        indexes = [
            models.Index(fields=['data_hora_agenda'], name='idx_data_agenda'),
            models.Index(fields=['carro'], name='idx_agendamento_carro'),
            models.Index(fields=['status'], name='idx_agendamento_status'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(data_hora_devolucao__gt=models.F('data_hora_agenda')),
                name='check_data_devolucao_maior'
            ),
            models.CheckConstraint(
                check=models.Q(km_final__gte=models.F('km_inicial')),
                name='check_km_final_maior'
            ),
        ]

class FotoAgendamento(models.Model):
    agendamento = models.ForeignKey(
        Agendamento, 
        on_delete=models.CASCADE,
        related_name='fotos'
    )
    imagem = models.ImageField(upload_to='agendamentos/fotos/')
    data_criacao = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"fotos {self.id} - Agendamento {self.agendamento.id}"
    