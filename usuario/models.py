from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission



class Usuario(models.Model):
    nome = models.CharField(unique=True, max_length=200)
    sobrenome = models.CharField(max_length=50)
    email = models.CharField(unique=True, max_length=200)
    senha = models.CharField(unique=True, max_length=6)

    class Meta:
        managed = True
        db_table = 'usuario'


class UsuarioCustomuser(models.Model):
    id = models.BigAutoField(primary_key=True)
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()
    matricula = models.CharField(max_length=100, blank=True, null=True)

    
    class Meta:
        managed = True
        db_table = 'usuario_customuser'

    groups = models.ManyToManyField(
        Group,
        verbose_name='groupos',
        blank=True,
        help_text='Grupos ao qual os usuários pertence.',
        related_name="ConjuntoUsuaario",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='Permissões do usúario',
        blank=True,
        help_text='Permissões específicas para este usuário.',
        related_name="ConjuntoUsuario",
        related_query_name="user",
    )


class CustomUserGroup(models.Model):
    id = models.BigAutoField(primary_key=True)
    customuser = models.ForeignKey(UsuarioCustomuser, models.DO_NOTHING)
    group = models.ForeignKey(Group, models.DO_NOTHING)

    class Meta:
        managed = True
        db_table = 'customusergroup'
        unique_together = (('customuser', 'group'),)


class CustomUserPermission(models.Model):
    id = models.BigAutoField(primary_key=True)
    customuser = models.ForeignKey(UsuarioCustomuser, models.DO_NOTHING)
    permission = models.ForeignKey(Permission, models.DO_NOTHING)

    class Meta:
        managed = True
        db_table = 'customuserpermission'
        unique_together = (('customuser', 'permission'),)