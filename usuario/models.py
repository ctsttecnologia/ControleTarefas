# usuario/models.py

# usuario/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _



# NOVO MODELO: Filial
class Filial(models.Model):
    """
    Modelo para cadastrar as unidades/filiais da empresa.
    """
    nome = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name="Nome da Filial"
    )
    
    class Meta:
        verbose_name = "Filial"
        verbose_name_plural = "Filiais"
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Usuario(AbstractUser):
    """
    Este é o seu modelo de usuário customizado.
    Ele herda todos os campos de AbstractUser, incluindo 'groups' e 'user_permissions'.
    Nós apenas adicionamos ou modificamos o que é estritamente necessário.
    """
    
    # Tornamos o email único e obrigatório.
    email = models.EmailField(_('endereço de e-mail'), unique=True)

    # Definindo o email como o campo de login principal.
    USERNAME_FIELD = 'email'
    
    # Campos requeridos ao criar um superusuário via linha de comando.
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    # NOVO CAMPO: Associa o usuário a uma filial.
    # on_delete=models.PROTECT impede que uma filial seja deletada se houver usuários nela.
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT, 
        related_name='usuarios', 
        verbose_name="Filial",
        null=True, # Provisoriamente True para permitir migrações em bancos existentes. Mude para False depois.
        blank=True # Provisoriamente True.
    )

    class Meta:
        verbose_name = _('usuário')
        verbose_name_plural = _('usuários')
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return self.get_full_name() or self.username

#
# Seus modelos Proxy continuam aqui, eles estão corretos.
#
class GrupoProxy(Group):
    class Meta:
        proxy = True
        verbose_name = 'Grupo de Permissões'
        verbose_name_plural = 'Grupos de Permissões'

class PermissaoProxy(Permission):
    class Meta:
        proxy = True
        verbose_name = 'Permissão'
        verbose_name_plural = 'Permissões'