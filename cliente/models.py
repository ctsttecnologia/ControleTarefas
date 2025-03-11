from django.db import models
from django.utils import timezone

class Logradouro(models.Model):
   id = models.AutoField(primary_key=True)
 

class Cliente(models.Model):
    nome = models.CharField(max_length=100)  # Campo nome
    logradouro = models.ForeignKey(Logradouro, on_delete=models.CASCADE, related_name='clientes')
    contrato = models.CharField(max_length=4, null=False)  # NOT NULL
    razao_social = models.CharField(max_length=100, null=False)  # NOT NULL
    unidade = models.IntegerField(null=True, blank=True)  
    cnpj = models.CharField(max_length=14, default='00000000000000')
    telefone = models.CharField(max_length=11, null=True, blank=True)  
    data_de_inicio = models.DateField(null=False)  # NOT NULL
    estatus = models.BooleanField(default=True)  # Valor padrão TRUE
    
   
    class Meta:
        db_table = 'cliente'  # Nome da tabela no banco de dados
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

class ClienteCliente(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)

    