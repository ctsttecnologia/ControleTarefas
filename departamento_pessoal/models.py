from django.db import models
from django.utils import timezone


class Logradouro(models.Model):
    # Campos do logradouro
    class Meta:
        managed = False
        db_table = 'logradouro'

class Documentos(models.Model):
    cpf = models.CharField(unique=True, max_length=11)
    pis = models.CharField(unique=True, max_length=12)
    ctps = models.CharField(unique=True, max_length=10)
    serie = models.CharField(unique=True, max_length=10)
    uf = models.CharField(max_length=3, blank=True, null=True)
    rg = models.CharField(unique=True, max_length=10)
    emissor = models.CharField(max_length=30, blank=True, null=True)
    reservista = models.IntegerField(blank=True, null=True)
    titulo_eleitor = models.IntegerField(db_column='titulo_Eleitor', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'documentos'

class Cbos(models.Model):
    codigo = models.CharField(unique=True, max_length=10)
    descricao = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'cbos'

class Cargos(models.Model):
    nome = models.CharField(unique=True, max_length=50)
    cbo = models.ForeignKey('Cbos', models.DO_NOTHING)
    descricao = models.CharField(max_length=45, null=True)

    class Meta:
        managed = False
        db_table = 'cargos'

class Departamentos(models.Model):
    nome = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'departamentos'

class Admissao(models.Model):
    cargo = models.ForeignKey('Cargos', models.DO_NOTHING)
    departamento = models.ForeignKey('Departamentos', models.DO_NOTHING)
    data_admissao = models.DateField(db_column='data_Admissao', blank=True, null=True)
    matricula = models.CharField(unique=True, max_length=10)
    salario = models.DecimalField(max_digits=10, decimal_places=2)
    data_cadastro = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'admissao'


class Funcionarios(models.Model):
    logradouro = models.ForeignKey('Logradouro', models.DO_NOTHING)
    documentos = models.ForeignKey(Documentos, models.DO_NOTHING)
    admissao = models.ForeignKey(Admissao, models.DO_NOTHING)
    nome = models.CharField(max_length=40)
    data_nascimento = models.DateField(db_column='data_Nascimento', blank=True, null=True)  # Field name made lowercase.
    naturalidade = models.CharField(max_length=30, blank=True, null=True)
    telefone = models.CharField(max_length=11, blank=True, null=True)
    email = models.CharField(unique=True, max_length=100, blank=True, null=True)
    pai = models.CharField(max_length=40, blank=True, null=True)
    mae = models.CharField(max_length=40, blank=True, null=True)
    filhos_qtda = models.PositiveIntegerField(db_column='filhos_Qtda', blank=True, null=True)  # Field name made lowercase.
    data_admissao = models.DateField(db_column='data_Admissao', blank=True, null=True)  # Field name made lowercase.
    pne = models.CharField(max_length=1, blank=True, null=True)
    descricao = models.CharField(max_length=250, blank=True, null=True)
    sexo = models.CharField(max_length=1, blank=True, null=True)
    peso = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    altura = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    estatus = models.IntegerField(blank=True, null=True)
    data_cadastro = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'funcionarios'




