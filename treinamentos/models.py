from django.db import models
from django.core.validators import MinValueValidator

class TipoTreinamento(models.Model):
    MODALIDADE_CHOICES = [
        ('I', 'Interno'),
        ('E', 'Externo'),
    ]
    
    nome = models.CharField(max_length=100, unique=True)
    modalidade = models.CharField(max_length=1, choices=MODALIDADE_CHOICES)
    descricao = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.nome

class Treinamento(models.Model):
    tipo_treinamento = models.ForeignKey(TipoTreinamento, on_delete=models.CASCADE)
    nome = models.CharField(max_length=200)
    data_inicio = models.DateField()
    data_vencimento = models.DateField()
    duracao = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text="Duração em horas")
    atividade = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    funcionario = models.CharField(max_length=100, help_text="Nome do funcionário responsável")
    cm = models.CharField(max_length=100, verbose_name="CM", help_text="Coordenador/Mentor")
    palestrante = models.CharField(max_length=100)
    hxh = models.PositiveIntegerField(verbose_name="HxH", help_text="Horas por hora")
    
    def __str__(self):
        return f"{self.nome} - {self.data_inicio}"
    
    class Meta:
        ordering = ['-data_inicio']
        verbose_name_plural = "Treinamentos"