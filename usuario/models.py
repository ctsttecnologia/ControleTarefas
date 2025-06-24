
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _ # Para tradução de strings



# ==============================================================================
# Modelo de Usuário Customizado
# Herda de AbstractUser para incluir todos os campos e funcionalidades padrão
# do usuário do Django (username, password, email, is_staff, is_active, etc.)
# ==============================================================================
class CustomUser(AbstractUser):
    # seus campos personalizados
    pass

class Usuario(AbstractUser):
    # Campo 'nome' customizado, conforme a tabela auth_user fornecida.
    # Adicionamos este campo, pois ele não é padrão no AbstractUser.
    nome = models.CharField(_('nome completo'), max_length=150, blank=True, null=True)
    email = models.EmailField(_('endereço de email'), unique=True, blank=False, null=False)

    # Definindo 'email' como o campo de login principal.
    # O campo 'username' ainda existirá, mas não será usado para login.
    USERNAME_FIELD = 'email'
    # Os campos em REQUIRED_FIELDS serão solicitados quando criar um superusuário
    # se USERNAME_FIELD não for 'username'.
    REQUIRED_FIELDS = ['username'] # 'username' ainda é requerido para AbstractUser,
 
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('grupos'),
        blank=True,
        help_text=_('Os grupos aos quais este usuário pertence. Um usuário terá todas as permissões concedidas a cada um de seus grupos.'),
        related_query_name="usuario", # Usado para consultas reversas
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('permissões de usuário'),
        blank=True,
        help_text=_('Permissões específicas para este usuário.'),
        related_query_name="usuario", # Usado para consultas reversas
    )

    class Meta:

        db_table = 'usuario'
        verbose_name = _('usuário')
        verbose_name_plural = _('usuários')
        ordering = ['-date_joined'] # Ordem padrão para listagens

    def __str__(self):
        # Retorna uma representação em string do objeto Usuario.
        # Como USERNAME_FIELD é 'email', usar self.email faz mais sentido.
        # Se 'nome' for preferível e sempre preenchido, pode ser 'self.nome'.
        return self.email or self.username # Retorna o email, ou o username se o email for vazio

# Modelo Proxy para Grupo (refere-se ao modelo Group padrão do Django)
class GrupoProxy(Group):
    class Meta:
        proxy = True # Define que este é um modelo proxy
        verbose_name = _('grupo')
        verbose_name_plural = _('grupos')

# Modelo Proxy para Permissão (refere-se ao modelo Permission padrão do Django)
class PermissaoProxy(Permission):
    class Meta:
        proxy = True # Define que este é um modelo proxy
        verbose_name = _('permissão')
        verbose_name_plural = _('permissões')

