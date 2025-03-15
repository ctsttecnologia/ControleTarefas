from django.db import models


class MinhaImagem(models.Model):
    titulo = models.CharField(max_length=100)
    imagem = models.ImageField(upload_to='imagens/')

    def __str__(self):
        return self.titulo
