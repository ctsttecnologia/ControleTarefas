from django.db import models
from django.utils import timezone

class Logradouro(models.Model):
    id = models.CharField(max_length=2, primary_key=True)  # Definido como chave primária

    class Meta:
        managed = False
        db_table = 'logradouro'

    def __str__(self):
        return self.id  # Representação legível do objeto

class Cliente(models.Model):
    nome = models.CharField(max_length=100)  # Campo nome
    logradouro = models.ForeignKey(Logradouro, on_delete=models.CASCADE, related_name='clientes')  # related_name alterado para 'clientes'
    contrato = models.CharField(max_length=4, default='0000')  # NOT NULL
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

    def __str__(self):
        return self.nome  # Representação legível do objeto

class Cliente_cliente(models.Model):
    id = models.CharField(max_length=2, primary_key=True)  # Definido como chave primária

    class Meta:
        managed = False
        db_table = 'cliente_cliente'   

class ClienteCliente(models.Model):
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='unidades_cliente')
    nome = models.CharField(max_length=100)

    class Meta:
        db_table = 'cliente_cliente'  # Nome da tabela no banco de dados

    def __str__(self):
        return self.nome  # Representação legível do objeto

    