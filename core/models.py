from django.db import models
from core.managers import FilialManager 


# --- ADICIONE ESTA NOVA CLASSE ---
class Filial(models.Model):
    
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Filial")
    cidade = models.CharField(max_length=100, blank=True)
    # Adicione outros campos que precisar

    def __str__(self):
        return self.nome

    class Meta:
        db_table ="core_filial"
        verbose_name = "Filial"
        verbose_name_plural = "Filiais"

class BaseModel(models.Model):
    """
    Um modelo base abstrato que outros modelos podem herdar.
    Ele fornece campos automáticos de data de criação e atualização.
    """
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        # Essencial: Isso diz ao Django para não criar uma tabela
        # no banco de dados para este modelo. Ele apenas serve de base.
        abstract = True
        ordering = ['-criado_em']