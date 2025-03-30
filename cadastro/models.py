from django.db import models
from .choices import ESTADOS_BRASIL
from django.utils import timezone


class Logradouro(models.Model):
    endereco = models.CharField(max_length=150)
    numero = models.IntegerField()
    cep = models.IntegerField()
    complemento = models.CharField(max_length=50, blank=True, null=True)
    bairro = models.CharField(max_length=60)
    cidade = models.CharField(max_length=60)
    estados = models.CharField(max_length=2, choices=ESTADOS_BRASIL)
    pais = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return f"{self.endereco}, {self.numero}, {self.bairro}, {self.cidade}/{self.estado}"
    
    class Meta:
        db_table = 'logradouro'  # opcional - define o nome exato da tabela