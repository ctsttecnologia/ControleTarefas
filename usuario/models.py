
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

# =============================================================================
# == MODELO USUARIO CORRIGIDO
# =============================================================================
class Usuario(AbstractUser):
    email = models.EmailField(_('endereço de e-mail'), unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    # CAMPO 1: Define a QUAIS filiais o usuário tem permissão de acesso.
    filiais_permitidas = models.ManyToManyField(
        Filial,
        verbose_name="Filiais Permitidas",
        help_text="Selecione as filiais que este usuário pode acessar.",
        blank=True,
        related_name="usuarios_permitidos"
    )

    # CAMPO 2: Define qual filial o usuário está usando no momento.
    filial_ativa = models.ForeignKey(
        Filial,
        verbose_name="Filial Ativa",
        help_text="A filial que está atualmente selecionada para este usuário.",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
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