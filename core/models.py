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