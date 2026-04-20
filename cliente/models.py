
# cliente/models.py

"""
Model principal do app Cliente.

Representa empresas contratantes vinculadas a uma Filial.
Cada cliente possui CNPJ único, contrato, endereço (via Logradouro)
e controle de datas de vigência.

Arquitetura de Filial:
  ✅ Model com campo `filial` direto → FilialManager
"""

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.managers import FilialManager
from core.validators import validate_cnpj, validate_email, validate_telefone
from logradouro.models import Logradouro
from usuario.models import Filial


class Cliente(models.Model):
    """
    Empresa contratante.

    Relacionamentos:
        - Filial (obrigatório, PROTECT)
        - Logradouro (obrigatório, PROTECT)

    Managers:
        - objects: FilialManager (filtra automaticamente por filial da sessão)
    """

    # =========================================================================
    # IDENTIFICAÇÃO
    # =========================================================================

    razao_social = models.CharField(
        _("Razão Social"),
        max_length=100,
    )
    nome = models.CharField(
        _("Nome Fantasia"),
        max_length=100,
    )
    cnpj = models.CharField(
        _("CNPJ"),
        max_length=18,
        unique=True,
        help_text=_("Formato: 00.000.000/0000-00"),
        validators=[validate_cnpj],
    )
    contrato = models.CharField(
        _("Número do Contrato (CM)"),
        max_length=4,
        default="0",
    )
    unidade = models.PositiveIntegerField(
        _("Unidade/Filial"),
        null=True,
        blank=True,
    )
    inscricao_estadual = models.CharField(
        _("Inscrição Estadual"),
        max_length=20,
        blank=True,
        null=True,
    )
    inscricao_municipal = models.CharField(
        _("Inscrição Municipal"),
        max_length=20,
        blank=True,
        null=True,
    )

    # =========================================================================
    # CONTATO
    # =========================================================================

    telefone = models.CharField(
        _("Telefone"),
        max_length=16,
        blank=True,
        null=True,
        help_text=_("Formato: (00) 00000-0000 ou (00) 0000-0000"),
        validators=[validate_telefone],
    )
    email = models.EmailField(
        _("E-mail"),
        max_length=100,
        blank=True,
        null=True,
        validators=[validate_email],
    )

    # =========================================================================
    # ENDEREÇO
    # =========================================================================

    logradouro = models.ForeignKey(
        Logradouro,
        on_delete=models.PROTECT,
        related_name="clientes",
        related_query_name="cliente",
        verbose_name=_("Endereço"),
    )

    # =========================================================================
    # VIGÊNCIA E STATUS
    # =========================================================================

    data_de_inicio = models.DateField(
        _("Data de Início"),
    )
    data_encerramento = models.DateField(
        _("Data de Encerramento"),
        null=True,
        blank=True,
    )
    estatus = models.BooleanField(
        _("Ativo?"),
        default=True,
    )

    # =========================================================================
    # OBSERVAÇÕES
    # =========================================================================

    observacoes = models.TextField(
        _("Observações"),
        blank=True,
        null=True,
    )

    # =========================================================================
    # CONTROLE INTERNO
    # =========================================================================

    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="clientes",
        related_query_name="cliente",
        verbose_name=_("Filial"),
    )
    data_cadastro = models.DateTimeField(
        _("Data de Cadastro"),
        auto_now_add=True,
    )
    data_atualizacao = models.DateTimeField(
        _("Última Atualização"),
        auto_now=True,
    )

    # =========================================================================
    # MANAGER
    # =========================================================================

    objects = FilialManager()

    # =========================================================================
    # META
    # =========================================================================

    class Meta:
        db_table = "cliente"
        verbose_name = _("Cliente")
        verbose_name_plural = _("Clientes")
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["cnpj"], name="idx_cliente_cnpj"),
            models.Index(fields=["razao_social"], name="idx_cliente_razao_social"),
            models.Index(fields=["contrato"], name="idx_cliente_contrato"),
            models.Index(fields=["filial", "estatus"], name="idx_cliente_filial_status"),
        ]
        permissions = [
            ("view_all_cliente", "Pode ver todos os clientes da filial"),
        ]

    # =========================================================================
    # STRING REPRESENTATION
    # =========================================================================

    def __str__(self):
        return self.razao_social

    # =========================================================================
    # URLS
    # =========================================================================

    def get_absolute_url(self):
        return reverse("cliente:cliente_detail", kwargs={"pk": self.pk})

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def cnpj_formatado(self):
        """
        Retorna CNPJ no formato XX.XXX.XXX/XXXX-XX.

        Limpa caracteres não numéricos antes de formatar,
        garantindo consistência independente do formato armazenado.
        """
        digitos = "".join(filter(str.isdigit, self.cnpj))
        if len(digitos) == 14:
            return (
                f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}"
                f"/{digitos[8:12]}-{digitos[12:]}"
            )
        return self.cnpj

    @property
    def is_encerrado(self):
        """Retorna True se o contrato foi encerrado."""
        from datetime import date

        if self.data_encerramento:
            return self.data_encerramento <= date.today()
        return False

    @property
    def endereco_completo(self):
        """Retorna o endereço completo via Logradouro vinculado."""
        if self.logradouro:
            return self.logradouro.get_endereco_completo()
        return _("Endereço não cadastrado")

    @property
    def nome_display(self):
        """
        Retorna representação amigável para exibição em listas.
        Prioriza razão social; inclui nome fantasia se diferente.
        """
        if self.nome and self.nome != self.razao_social:
            return f"{self.razao_social} ({self.nome})"
        return self.razao_social
