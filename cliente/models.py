from django.db import models

class Logradouro(models.Model):
    endereco = models.CharField(max_length=200)
    cep = models.CharField(max_length=10)

    def __str__(self):
        return self.endereco

class Cliente(models.Model):
    logradouro = models.ForeignKey(Logradouro, on_delete=models.CASCADE)
    contrato = models.CharField(max_length=4)
    razao_social = models.CharField(max_length=100)
    unidade = models.IntegerField(blank=True, null=True)
    cnpj = models.CharField(unique=True, max_length=18)
    telefone = models.CharField(max_length=11, blank=True, null=True)
    data_de_inicio = models.DateField(blank=True, null=True)
    estatus = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.razao_social

class ClienteCliente(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome