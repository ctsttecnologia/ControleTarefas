from django.db import models
from django.utils import timezone


class FichaEPI(models.Model):
    nome_colaborador = models.CharField(max_length=100)
    
    equipamento = models.CharField(max_length=100)
    ca_equipamento = models.CharField(max_length=50)
    data_entrega = models.DateField()
    data_devolucao = models.DateField(null=True, blank=True)
    contrato_id = models.IntegerField()
    quantidade = models.IntegerField()
    descricao = models.TextField(blank=True, null=True)
    assinatura_colaborador = models.ImageField(upload_to='assinaturas/', null=False, blank=False)  # Novo campo


    def __str__(self):
        return f"{self.nome_colaborador} - {self.equipamento}"

class EquipamentosSeguranca(models.Model):
    nome_equioamento = models.CharField(max_length=100)
    tipo = models.CharField(max_length=3)
    codigo_ca = models.CharField(db_column='codigo_CA', unique=True, max_length=10, blank=True, null=True)  # Field name made lowercase.
    descricao = models.TextField(blank=True, null=True)
    quantidade_estoque = models.IntegerField(blank=True, null=True)
    data_validade = models.DateField(blank=True, null=True)
    ativo = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'equipamentos_seguranca'

