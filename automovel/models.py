from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import os
from datetime import timedelta

class Carro(models.Model):
    # Validador personalizado para placas de carro (formato brasileiro)
    placa_validator = RegexValidator(
        regex=r'^[A-Z]{3}\d{1}[A-Z]{1}\d{2}$|^[A-Z]{3}\d{4}$',
        message=_('Formato de placa inválido. Use AAA1A11 ou AAA1111')
    )
    
    # Campos com validações avançadas
    placa = models.CharField(
        max_length=10,
        validators=[placa_validator],
        unique=True,
        verbose_name=_('Placa do Veículo'),
        help_text=_('Formato: AAA1A11 ou AAA1111')
    )
    
    modelo = models.CharField(
        max_length=50,
        verbose_name=_('Modelo do Veículo')
    )
    
    marca = models.CharField(
        max_length=50,
        verbose_name=_('Marca do Veículo')
    )
    
    cor = models.CharField(
        max_length=30,
        verbose_name=_('Cor do Veículo')
    )
    
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
    
    # Campos calculados/adicionais
    ativo = models.BooleanField(
        default=True,
        verbose_name=_('Veículo Ativo na Frota')
    )
    
    observacoes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Observações')
    )
    
    # Métodos avançados
    def clean(self):
        """Validações adicionais no nível do modelo"""
        super().clean()
        
        # Valida se a data da próxima manutenção é posterior à última
        if self.data_ultima_manutencao and self.data_proxima_manutencao:
            if self.data_proxima_manutencao <= self.data_ultima_manutencao:
                raise ValidationError({
                    'data_proxima_manutencao': _('A data da próxima manutenção deve ser após a última manutenção.')
                })
    
    def save(self, *args, **kwargs):
        """Sobrescrita do método save para lógica adicional"""
        self.placa = self.placa.upper()  # Garante placa em maiúsculas
        self.full_clean()  # Executa todas as validações
        super().save(*args, **kwargs)
    
    def calcular_proxima_manutencao(self, dias=90):
        """Calcula automaticamente a próxima manutenção baseada na última"""
        if self.data_ultima_manutencao:
            self.data_proxima_manutencao = self.data_ultima_manutencao + timedelta(days=dias)
            self.save()
    
    def verificar_manutencao_pendente(self):
        """Verifica se há manutenção pendente"""
        if self.data_proxima_manutencao:
            return self.data_proxima_manutencao <= timezone.now().date()
        return False
    
    @property
    def idade(self):
        """Retorna a idade do veículo em anos"""
        return timezone.now().year - self.ano
    
    @property
    def status(self):
        """Retorna status formatado do veículo"""
        if not self.ativo:
            return _('Inativo')
        if self.verificar_manutencao_pendente():
            return _('Ativo - Manutenção Pendente')
        return _('Ativo')
    
    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placa} ({self.ano})"
    
    class Meta:
        db_table = 'automovel_carro'
        verbose_name = _('Veículo')
        verbose_name_plural = _('Veículos')
        ordering = ['marca', 'modelo']
        indexes = [
            models.Index(fields=['placa'], name='idx_carro_placa'),
            models.Index(fields=['marca', 'modelo'], name='idx_carro_marca_modelo'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['placa', 'renavan'],
                name='unique_placa_renavan'
            ),
        ]

class Agendamento(models.Model):
    SIM_NAO_CHOICES = [
        ('S', _('Sim')),
        ('N', _('Não')),
    ]
    
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
    
    funcionario = models.CharField(
        max_length=100,
        verbose_name=_('Funcionário Responsável')
    )
    
    data_hora_agenda = models.DateTimeField(
        verbose_name=_('Data/Hora do Agendamento')
    )
    
    data_hora_devolucao = models.DateTimeField(
        verbose_name=_('Data/Hora da Devolução'),
        null=True,
        blank=True
    )
    
    cm = models.CharField(
        max_length=20,
        verbose_name=_('Código do Contrato (CM)')
    )
    
    descricao = models.TextField(
        blank=True,
        verbose_name=_('Descrição do Agendamento')
    )
    
    pedagio = models.CharField(
        max_length=1,
        choices=SIM_NAO_CHOICES,
        default='N',
        verbose_name=_('Pedágio Necessário?')
    )
    
    abastecimento = models.CharField(
        max_length=1,
        choices=SIM_NAO_CHOICES,
        default='N',
        verbose_name=_('Abastecimento Necessário?')
    )
    
    km_inicial = models.PositiveIntegerField(
        verbose_name=_('Quilometragem Inicial')
    )
    
    km_final = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('Quilometragem Final')
    )
    
    fotos = models.ImageField(
        upload_to='agendamentos/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name=_('Fotos do Veículo')
    )
    
    assinatura = models.TextField(
        blank=True,
        verbose_name=_('Assinatura Digital')
    )
    
    responsavel = models.CharField(
        max_length=100,
        verbose_name=_('Responsável pelo Agendamento')
    )
    
    ocorrencia = models.TextField(
        blank=True,
        verbose_name=_('Ocorrências Durante o Uso')
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='agendado',
        verbose_name=_('Status do Agendamento')
    )
    
    cancelar_agenda = models.CharField(
        max_length=1,
        choices=SIM_NAO_CHOICES,
        default='N',
        verbose_name=_('Cancelar Agendamento?')
    )
    
    motivo_cancelamento = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Motivo do Cancelamento')
    )
    
    def clean(self):
        """Validações complexas do agendamento"""
        super().clean()
        
        # Validação de datas
        if self.data_hora_devolucao and self.data_hora_agenda:
            if self.data_hora_devolucao <= self.data_hora_agenda:
                raise ValidationError({
                    'data_hora_devolucao': 'A data de devolução deve ser após a data de agendamento.'
                })
        
        # Validação de quilometragem
        if self.km_final and self.km_inicial:
            if self.km_final < self.km_inicial:
                raise ValidationError({
                    'km_final': 'A quilometragem final não pode ser menor que a inicial.'
                })
        
        # Validação de cancelamento
        if self.cancelar_agenda == 'S' and not self.motivo_cancelamento:
            raise ValidationError({
                'motivo_cancelamento': 'Motivo do cancelamento é obrigatório quando o agendamento é cancelado.'
            })
        
        if self.status == 'cancelado' and not self.motivo_cancelamento:
            raise ValidationError({
                'motivo_cancelamento': 'Motivo do cancelamento é obrigatório para status "Cancelado".'
            })
    
    def save(self, *args, **kwargs):
        """Lógica adicional ao salvar"""
        # Atualiza status se cancelado
        if self.cancelar_agenda == 'S':
            self.status = 'cancelado'
        
        # Atualiza status se concluído
        if self.data_hora_devolucao and not self.cancelar_agenda == 'S':
            self.status = 'concluido'
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def calcular_quilometragem_percorrida(self):
        """Retorna a quilometragem percorrida"""
        if self.km_final and self.km_inicial:
            return self.km_final - self.km_inicial
        return 0
    
    def duracao_agendamento(self):
        """Calcula a duração total do agendamento"""
        if self.data_hora_devolucao:
            return self.data_hora_devolucao - self.data_hora_agenda
        return None
    
    @property
    def necessita_abastecimento(self):
        """Retorna se precisa de abastecimento"""
        return self.abastecimento == 'S'
    
    @property
    def necessita_pedagio(self):
        """Retorna se precisa de pedágio"""
        return self.pedagio == 'S'
    
    def finalizar_agendamento(self, km_final, ocorrencia=None):
        """Método para finalizar o agendamento"""
        self.km_final = km_final
        self.ocorrencia = ocorrencia
        self.data_hora_devolucao = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Agendamento {self.id} - {self.carro.placa} ({self.data_hora_agenda})"
    
    class Meta:
        db_table = 'automovel_agendamento'
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

        