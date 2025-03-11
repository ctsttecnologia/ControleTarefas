from django.db import models

class Estados(models.Model):
    uf = models.CharField(max_length=2)

    class Meta:
        managed = False
        db_table = 'estados'


class Logradouro(models.Model):
    estados = models.ForeignKey(Estados, models.DO_NOTHING)
    endereco = models.CharField(max_length=150)
    numero = models.IntegerField()
    complemento = models.CharField(max_length=50, blank=True, null=True)
    bairro = models.CharField(max_length=30)
    cidade = models.CharField(max_length=30)
    cep = models.IntegerField()
    pais = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'logradouro'
