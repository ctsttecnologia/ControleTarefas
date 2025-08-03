
# automovel/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from core.managers import FilialManager
from usuario.models import Filial

class Carro(models.Model):
    placa = models.CharField(max_length=10, unique=True)
    modelo = models.CharField(max_length=50)
    marca = models.CharField(max_length=50)
    cor = models.CharField(max_length=30)
    ano = models.PositiveIntegerField()
    renavan = models.CharField(max_length=20, unique=True)
    data_ultima_manutencao = models.DateField(null=True, blank=True)
    data_proxima_manutencao = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, null=True)
    disponivel = models.BooleanField(default=True)
    # CORREÇÃO: related_name único e campo obrigatório.
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='carros', null=True, blank=False)

    # Manager Padrão
    objects = FilialManager()

    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placa}"

    class Meta:
        verbose_name = "Carro"
        verbose_name_plural = "Carros"
        ordering = ['marca', 'modelo']

class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('agendado', 'Agendado'),
        ('em_andamento', 'Em Andamento'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]

    funcionario = models.CharField(max_length=100)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    carro = models.ForeignKey(Carro, on_delete=models.PROTECT, related_name='agendamentos')
    data_hora_agenda = models.DateTimeField()
    data_hora_devolucao = models.DateTimeField()
    cm = models.CharField(max_length=20, verbose_name="Centro de Custo/Motorista")
    descricao = models.TextField()
    pedagio = models.BooleanField(default=False)
    abastecimento = models.BooleanField(default=False)
    km_inicial = models.PositiveIntegerField()
    km_final = models.PositiveIntegerField(null=True, blank=True)
    foto_principal = models.ImageField(upload_to='agendamentos/', null=True, blank=True)
    assinatura = models.TextField(blank=True, null=True, verbose_name="Assinatura Digital")
    responsavel = models.CharField(max_length=100)
    ocorrencia = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='agendado')
    cancelar_agenda = models.BooleanField(default=False)
    motivo_cancelamento = models.TextField(blank=True, null=True)
    # CORREÇÃO: related_name único e campo obrigatório.
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='agendamentos', null=True, blank=False)

    # Manager Padrão
    objects = FilialManager()

    def __str__(self):
        return f"Agendamento #{self.id} - {self.carro.placa} para {self.funcionario}"

    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ['-data_hora_agenda']

class Checklist(models.Model):
    TIPO_CHOICES = [('saida', 'Saída'), ('retorno', 'Retorno'), ('vistoria', 'Vistoria')]
    STATUS_CHOICES = [('ok', 'OK'), ('danificado', 'Danificado'), ('nao_aplicavel', 'Não Aplicável')]

    agendamento = models.ForeignKey(Agendamento, on_delete=models.CASCADE, related_name='checklists')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    data_hora = models.DateTimeField(default=timezone.now, verbose_name="Data/Hora")
    km_inicial = models.PositiveIntegerField()
    km_final = models.PositiveIntegerField(null=True, blank=True)
    revisao_frontal_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_frontal = models.ImageField(upload_to='checklist/frontal/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    revisao_trazeira_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_trazeira = models.ImageField(upload_to='checklist/trazeira/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    revisao_lado_motorista_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_lado_motorista = models.ImageField(upload_to='checklist/lado_motorista/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    revisao_lado_passageiro_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_lado_passageiro = models.ImageField(upload_to='checklist/lado_passageiro/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    observacoes_gerais = models.TextField(blank=True, null=True)
    anexo_ocorrencia = models.TextField(blank=True, null=True)
    assinatura = models.TextField(blank=True, null=True, verbose_name="Assinatura Digital")
    confirmacao = models.BooleanField(default=False)
    # CORREÇÃO: related_name único e campo obrigatório.
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='checklists', null=True, blank=False)
    
    # Manager Padrão
    objects = FilialManager()

    def __str__(self):
        return f"Checklist ({self.get_tipo_display()}) para Agendamento #{self.agendamento.id}"

    class Meta:
        verbose_name = "Checklist"
        verbose_name_plural = "Checklists"
        ordering = ['-data_hora']
        unique_together = ('agendamento', 'tipo')

class Foto(models.Model):
    agendamento = models.ForeignKey(Agendamento, on_delete=models.CASCADE, related_name='fotos')
    imagem = models.ImageField(upload_to='fotos/')
    data_criacao = models.DateTimeField(default=timezone.now)
    observacao = models.TextField(blank=True, null=True)
    # CORREÇÃO: related_name único e campo obrigatório.
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='fotos', null=True, blank=False)

    # Manager Padrão
    objects = FilialManager()

    def __str__(self):
        return f"Foto #{self.id} - {self.agendamento}"

    class Meta:
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
        ordering = ['-data_criacao']

