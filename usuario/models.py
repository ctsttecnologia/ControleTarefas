
# usuario/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _

from core.constants import (
    GRUPO_ADMINISTRADOR,
    GRUPO_GERENTE,
    GRUPO_COORDENADOR,
    GRUPO_TECNICO,
    GRUPO_ASSISTENTE,
    GRUPO_USUARIO_COMUM,
    GRUPO_DEPARTAMENTO_PESSOAL,
    GRUPO_PLANEJAMENTO,
    GRUPO_SUPRIMENTOS,
    GRUPO_GESTAO_QUALIDADE,
    GRUPO_SST_SEGURANCA,
    GRUPO_DASHBOARD_FULL,
)


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

        permissions = [
            ("pode_ver_dashboard_geral", "Pode ver o dashboard principal"),
            ("pode_acessar_relatorios_filial", "Pode acessar relatórios da filial"),
            ("pode_editar_card_principal", "Pode editar os cards principais"),
        ]

    def __str__(self):
        return self.nome

# =============================================================================
# == MODELO USUARIO 
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
    
    # ---------- Perfis hierárquicos ----------
    
    @property
    def is_gerente(self) -> bool:
        return self.groups.filter(name=GRUPO_GERENTE).exists()

    @property
    def is_coordenador(self) -> bool:
        return self.groups.filter(name=GRUPO_COORDENADOR).exists()

    @property
    def is_tecnico(self) -> bool:
        return self.groups.filter(name=GRUPO_TECNICO).exists()

    @property
    def is_assistente(self) -> bool:
        return self.groups.filter(name=GRUPO_ASSISTENTE).exists()

    @property
    def is_usuario_comum(self) -> bool:
        return self.groups.filter(name=GRUPO_USUARIO_COMUM).exists()

    # ---------- Setores ----------
    @property
    def is_do_dp(self) -> bool:
        return self.groups.filter(name=GRUPO_DEPARTAMENTO_PESSOAL).exists()

    @property
    def is_do_planejamento(self) -> bool:
        return self.groups.filter(name=GRUPO_PLANEJAMENTO).exists()

    @property
    def is_do_suprimentos(self) -> bool:
        return self.groups.filter(name=GRUPO_SUPRIMENTOS).exists()

    @property
    def is_da_qualidade(self) -> bool:
        return self.groups.filter(name=GRUPO_GESTAO_QUALIDADE).exists()

    @property
    def is_do_sst(self) -> bool:
        return self.groups.filter(name=GRUPO_SST_SEGURANCA).exists()

    # ---------- Feature flags ----------
    @property
    def tem_dashboard_full(self) -> bool:
        return self.groups.filter(name=GRUPO_DASHBOARD_FULL).exists()

    # ---------- Helper genérico ----------
    def pertence_ao_grupo(self, nome_grupo: str) -> bool:
        """Verifica pertencimento a qualquer grupo pelo nome."""
        return self.groups.filter(name=nome_grupo).exists()
    
    # Propriedade para verificar se o usuário é Administrador
    @property
    def is_administrador(self):
        # Verifica se é um Superusuário OU se pertence ao grupo 'Administrador'
        return self.is_superuser or self.groups.filter(name=GRUPO_ADMINISTRADOR).exists()

    
class GroupCardPermissions(models.Model):
    # A Foreign Key para o modelo de grupo do Django
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    
    # Campo JSON para armazenar uma lista dos IDs dos cartões
    # Exemplo: ['tarefas', 'clientes', 'dp']
    cards_visiveis = models.JSONField(default=list)

    def __str__(self):
        return f"Permissões de Cartão para o Grupo: {self.group.name}"

    class Meta:
        verbose_name = "Permissão de Cartão de Grupo"
        verbose_name_plural = "Permissões de Cartões de Grupo"

# Seus modelos Proxy 
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

        