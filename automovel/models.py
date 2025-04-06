from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Carro(models.Model):
    placa = models.CharField(max_length=10, default='', blank=True)
    modelo = models.CharField(max_length=50, default='', blank=True)
    marca = models.CharField(max_length=50, default='', blank=True)
    cor = models.CharField(max_length=30, default='', blank=True)
    ano = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(timezone.now().year + 1)
        ]
    )
    renavan = models.CharField(max_length=20, primary_key=True)
    data_ultima_manutencao = models.DateField()
    data_proxima_manutencao = models.DateField()
    
    
    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.renavan}"

    class Carro(models.Model):
    # seus campos aqui...
        class Meta:
            db_table = 'automovel'  # Força o nome da tabela


class Agendamento(models.Model):
    SIM_NAO_CHOICES = [
        ('S', 'Sim'),
        ('N', 'Não'),
    ]
    carro = models.ForeignKey('Carro', on_delete=models.CASCADE, related_name='agendamentos')
    funcionario = models.CharField(max_length=100)
    data_hora_agenda = models.DateTimeField()
    data_hora_devolucao = models.DateTimeField()
    cm = models.CharField(max_length=20, verbose_name="CM")
    km_inicial = models.PositiveIntegerField()
    km_final = models.PositiveIntegerField(blank=True, null=True)
    fotos = models.ImageField(upload_to='agendamentos/', blank=True, null=True)
    assinatura = models.TextField(blank=True)  # Armazenará a assinatura digital
    responsavel = models.CharField(max_length=100)
    cancelar_agenda = models.CharField(max_length=1, choices=SIM_NAO_CHOICES, default='N')

    def __str__(self):
        return f"Agendamento {self.id} - {self.carro} ({self.data_hora_agenda})"

    class Meta:
        db_table = 'automovel_agendamento'  # Nome explícito da tabela
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        ordering = ['-data_hora_agenda']  # Ordenação padrão
        indexes = [
            models.Index(fields=['data_hora_agenda'], name='idx_data_agenda'),
            models.Index(fields=['carro'], name='idx_agendamento_carro'),
        ]