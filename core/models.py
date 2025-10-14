from django.db import models


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

