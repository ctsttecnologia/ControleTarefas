# G:\Projetos\notifications\models.py

from django.db import models
from django.conf import settings

# Garanta que a classe se chama exatamente "Notificacao"
class Notificacao(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notificacoes'
    )
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    url_destino = models.URLField(blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Corrigido para acessar o username do usuário relacionado
        return f"Notificação para {self.usuario.username}"

    class Meta:
        ordering = ['-data_criacao']