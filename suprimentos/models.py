# suprimentos/models.py
"""
Models do app Suprimentos.

Inclui:
  - Modelos abstratos (TimestampedModel, BaseAnexo, BaseHistorico)
  - Choices reutilizáveis
  - Parceiro, Material, Contrato, VerbaContrato
  - Pedido + Anexos + Histórico + Itens
  - SolicitacaoCompra + Anexos + Histórico
  - EstoqueConsumo
"""

import os

import uuid
from decimal import Decimal
from pathlib import Path
from django.db.models import Sum, F
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.managers import FilialManager
from core.upload import make_upload_path
from core.validators import SecureFileValidator
from logradouro.models import Logradouro
from usuario.models import Filial
from suprimentos.utils import _registrar_historico


# ═════════════════════════════════════════════════════════════════════════════
# MODELOS ABSTRATOS 
# ═════════════════════════════════════════════════════════════════════════════

class TimestampedModel(models.Model):
    """Adiciona criado_em / atualizado_em automáticos."""
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseAnexo(TimestampedModel):
    """
    Comportamento comum de anexos.

    ⚠️ Subclasses DEVEM definir:
       - arquivo (FileField com upload_to próprio)
       - FK para o objeto pai (pedido, solicitacao, etc.)
       - enviado_por (FK para AUTH_USER_MODEL) — redefinir conforme política
    """
    descricao = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Descrição opcional do anexo",
    )

    class Meta:
        abstract = True
        ordering = ["-criado_em"]

    # ---------- Properties úteis ----------
    @property
    def nome_arquivo(self) -> str:
        return Path(self.arquivo.name).name if self.arquivo else ""

    @property
    def extensao(self) -> str:
        return Path(self.arquivo.name).suffix.lower().lstrip(".") if self.arquivo else ""

    @property
    def is_imagem(self) -> bool:
        return self.extensao in {"jpg", "jpeg", "png", "gif", "webp", "bmp"}

    @property
    def is_pdf(self) -> bool:
        return self.extensao == "pdf"

    @property
    def tamanho_humano(self) -> str:
        try:
            size = self.arquivo.size
        except (FileNotFoundError, ValueError):
            return "—"
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def __str__(self) -> str:
        return self.nome_arquivo or f"Anexo #{self.pk}"


class BaseHistorico(TimestampedModel):
    """Comportamento comum de histórico/auditoria.
    
    Herda `criado_em` e `atualizado_em` de TimestampedModel.
    """
    acao = models.CharField(max_length=100, blank=True, default="")
    dados_anteriores = models.JSONField(null=True, blank=True)
    dados_novos = models.JSONField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["-criado_em"]


# ═════════════════════════════════════════════════════════════════════════════
# CHOICES REUTILIZÁVEIS
# ═════════════════════════════════════════════════════════════════════════════

class CategoriaMaterial(models.TextChoices):
    CONSUMO = "CONSUMO", "Consumo"
    EPI = "EPI", "EPI"
    FERRAMENTA = "FERRAMENTA", "Ferramenta"


class TipoMaterial(models.TextChoices):
    CIVIL = "CIVIL", "Civil"
    ELETRICA = "ELETRICA", "Elétrica"
    HIDRAULICA = "HIDRAULICA", "Hidráulica"
    LIMPEZA = "LIMPEZA", "Limpeza"
    ESCRITORIO = "ESCRITORIO", "Escritório"
    CREME = "CREME", "Creme"
    EPI = "EPI", "EPI"
    PRODUTO_QUIMICO = "PRODUTO QUIMICO", "Produto Químico"
    AR_CONDICIONADO = "AR CONDICIONADO", "Ar Condicionado"
    PISCINA = "PISCINA", "Piscina"
    INFORMATICA = "INFORMATICA", "Informática"


class UnidadeMedida(models.TextChoices):
    PÇ = "PÇ", "Peça"
    PAR = "PAR", "Par"
    LATA = "LATA", "Lata"
    ROLO = "ROLO", "Rolo"
    GALAO = "GALAO", "Galão"
    PACOTE = "PACOTE", "Pacote"
    JOGO = "JOGO", "Jogo"
    KIT = "KIT", "Kit"
    CAIXA = "CAIXA", "Caixa"
    FRASCO = "FRASCO", "Frasco"
    POTE = "POTE", "Pote"
    KG = "KG", "Kg"
    METRO = "METRO", "Metro"
    LITRO = "LITRO", "Litro"
    CARTELA = "CARTELA", "Cartela"
    UNID = "UNID", "Unidade"
    TON = "TON", "Tonelada"
    

class TipoObra(models.TextChoices):
    CM = "CM", "CM - Contrato de Manutenção"
    CR = "CR", "CR - Contrato de Reforma"
    VE = "VE", "VE - Venda"


class TipoNotaFiscal(models.TextChoices):
    MATERIAL = "MATERIAL", "Material"
    SERVICO = "SERVICO", "Serviço"
    MATERIAL_SERVICO = "MATERIAL_SERVICO", "Material/Serviço"


# ═════════════════════════════════════════════════════════════════════════════
# PARCEIRO
# ═════════════════════════════════════════════════════════════════════════════

class Parceiro(models.Model):
    razao_social = models.CharField(max_length=255, verbose_name=_("Razão Social"), blank=True)
    nome_fantasia = models.CharField(max_length=255, verbose_name=_("Nome Fantasia / Nome do Fabricante"))
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True, verbose_name=_("CNPJ"))
    inscricao_estadual = models.CharField(max_length=20, blank=True, verbose_name=_("Inscrição Estadual"))
    contato = models.CharField(max_length=100, blank=True, verbose_name=_("Pessoa de Contato"))
    telefone = models.CharField(max_length=20, blank=True, verbose_name=_("Telefone"))
    celular = models.CharField(max_length=20, blank=True, verbose_name=_("Celular"))
    email = models.EmailField(blank=True, verbose_name=_("E-mail"))
    site = models.URLField(blank=True, verbose_name=_("Site"))
    endereco = models.ForeignKey(
        Logradouro, on_delete=models.PROTECT,
        related_name="parceiros", verbose_name=_("Endereço"),
        null=True, blank=True,
    )
    observacoes = models.TextField(blank=True, verbose_name=_("Observações"))
    eh_fabricante = models.BooleanField(default=False, verbose_name=_("É Fabricante?"))
    eh_fornecedor = models.BooleanField(default=False, verbose_name=_("É Fornecedor?"))
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name="parceiros", verbose_name=_("Filial"),
        null=True, blank=True,
    )
    objects = FilialManager()

    class Meta:
        verbose_name = _("Parceiro")
        verbose_name_plural = _("Parceiros")
        ordering = ["nome_fantasia"]

    def __str__(self):
        return self.nome_fantasia or self.razao_social

    def get_absolute_url(self):
        return reverse("suprimentos:parceiro_detail", kwargs={"pk": self.pk})


# ═════════════════════════════════════════════════════════════════════════════
# 1. CATÁLOGO DE MATERIAIS
# ═════════════════════════════════════════════════════════════════════════════

class Material(models.Model):
    """Catálogo centralizado de materiais (EPI, Consumo, Ferramenta)."""

    codigo = models.CharField(
        _("Código"), max_length=20, unique=True, blank=True,
        help_text=_("Gerado automaticamente se deixado em branco."),
    )
    descricao = models.CharField(_("Descrição"), max_length=500)
    classificacao = models.CharField(
        _("Classificação"), max_length=20,
        choices=CategoriaMaterial.choices,
    )
    tipo = models.CharField(
        _("Tipo"), max_length=30,
        choices=TipoMaterial.choices,
    )
    marca = models.CharField(
        _("Marca"), max_length=100, blank=True, default="",
    )
    unidade = models.CharField(
        _("Unidade"), max_length=20,
        choices=UnidadeMedida.choices,
        default=UnidadeMedida.PÇ,
    )
    valor_unitario = models.DecimalField(
        _("Valor Unitário (R$)"), max_digits=10, decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # ── Vínculos com estoque de outros módulos ───────────────────────────────
    equipamento_epi = models.ForeignKey(
        "seguranca_trabalho.Equipamento",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="materiais_vinculados",
        verbose_name=_("Equipamento EPI vinculado"),
        help_text=_(
            "Para materiais EPI: vincule ao equipamento de SST "
            "para entrada automática no estoque."
        ),
    )
    ferramenta_ref = models.ForeignKey(
        "ferramentas.Ferramenta",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="materiais_vinculados",
        verbose_name=_("Ferramenta vinculada"),
        help_text=_(
            "Para ferramentas: vincule para atualizar quantidade "
            "ao receber pedido."
        ),
    )

    # ── Vínculos com Tributação ──────────────────────────────────────────────
    ncm = models.ForeignKey(
        "tributacao.NCM",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="materiais",
        verbose_name=_("NCM"),
        help_text=_(
            "Classificação fiscal do material "
            "(Nomenclatura Comum do Mercosul)"
        ),
    )
    grupo_tributario = models.ForeignKey(
        "tributacao.GrupoTributario",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="materiais",
        verbose_name=_("Grupo Tributário"),
        help_text=_(
            "Perfil fiscal para cálculo automático de impostos na compra"
        ),
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name="materiais",
        null=True, blank=True,
        verbose_name=_("Filial"),
    )

    ativo = models.BooleanField(_("Ativo"), default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Material")
        verbose_name_plural = _("Materiais")
        ordering = ["classificacao", "tipo", "descricao"]
        indexes = [
            models.Index(fields=["classificacao", "tipo"]),
            models.Index(fields=["descricao"]),
        ]

    def __str__(self):
        marca = f" ({self.marca})" if self.marca else ""
        return f"{self.descricao}{marca}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            prefix = self.classificacao[:3].upper()
            self.codigo = f"{prefix}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def calcular_custo_compra(self, valor_total, quantidade=1):
        """
        Calcula custo real de aquisição usando o grupo tributário.
        Se não houver grupo, retorna valor bruto.
        """
        if not self.grupo_tributario:
            valor = Decimal(str(valor_total))
            qtd = Decimal(str(quantidade)) if quantidade > 0 else Decimal("1")
            return {
                "valor_produtos": valor,
                "custo_real": valor,
                "total_creditos": Decimal("0.00"),
                "total_impostos": Decimal("0.00"),
                "total_nfe": valor,
                "custo_unitario": (valor / qtd).quantize(Decimal("0.01")),
                "percentual_economia": Decimal("0.00"),
                "sem_grupo": True,
            }
        return self.grupo_tributario.calcular_impostos(valor_total, quantidade)

    @property
    def tem_vinculo_estoque(self):
        """Verifica se o material está vinculado a um item de estoque."""
        if self.classificacao == CategoriaMaterial.EPI:
            return self.equipamento_epi is not None
        elif self.classificacao == CategoriaMaterial.FERRAMENTA:
            return self.ferramenta_ref is not None
        return True

    @property
    def info_tributaria_unitaria(self):
        """Calcula impostos para 1 unidade do material."""
        if not self.grupo_tributario:
            return {"sem_grupo": True}

        try:
            calc = self.calcular_custo_compra(self.valor_unitario, 1)
            calc["sem_grupo"] = False

            pct = Decimal("0.00")
            if self.valor_unitario > 0:
                creditos = calc.get("total_creditos", Decimal("0.00"))
                pct = ((creditos / self.valor_unitario) * 100).quantize(
                    Decimal("0.01")
                )
            calc["percentual_economia"] = pct
            return calc
        except Exception:
            return {"sem_grupo": True}


# ═════════════════════════════════════════════════════════════════════════════
# 2. CONTRATO / CM
# ═════════════════════════════════════════════════════════════════════════════

class Contrato(models.Model):
    """
    Contrato (CM) vinculado obrigatoriamente a uma Filial.
    Cada contrato tem verbas mensais (VerbaContrato).
    """

    cm = models.CharField(_("CM (Código)"), max_length=20, unique=True)
    cliente = models.CharField(_("Cliente"), max_length=255)
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name="contratos", verbose_name=_("Filial"),
    )
    ativo = models.BooleanField(_("Ativo"), default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = FilialManager()

    class Meta:
        verbose_name = _("Contrato")
        verbose_name_plural = _("Contratos")
        ordering = ["cm"]

    def __str__(self):
        return f"CM {self.cm} - {self.cliente}"

    def get_absolute_url(self):
        return reverse("suprimentos:contrato_detalhe", kwargs={"pk": self.pk})

    def verba_do_mes(self, ano=None, mes=None):
        """Retorna a VerbaContrato do mês atual (cria se não existir)."""
        hoje = timezone.now().date()
        ano = ano or hoje.year
        mes = mes or hoje.month
        verba, _ = VerbaContrato.objects.get_or_create(
            contrato=self, ano=ano, mes=mes,
            defaults={
                "verba_epi": Decimal("0.00"),
                "verba_consumo": Decimal("0.00"),
                "verba_ferramenta": Decimal("0.00"),
            },
        )
        return verba


# ═════════════════════════════════════════════════════════════════════════════
# 3. VERBA MENSAL DO CONTRATO
# ═════════════════════════════════════════════════════════════════════════════

class VerbaContrato(models.Model):
    """
    Verbas mensais de um contrato. Permite histórico mês a mês
    e comparação Verba × Compra (indicadores).
    """

    contrato = models.ForeignKey(
        Contrato, on_delete=models.CASCADE,
        related_name="verbas", verbose_name=_("Contrato"),
    )
    ano = models.PositiveSmallIntegerField(_("Ano"))
    mes = models.PositiveSmallIntegerField(_("Mês"))

    verba_epi = models.DecimalField(
        _("Verba EPI (R$)"), max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
    )
    verba_consumo = models.DecimalField(
        _("Verba Consumo (R$)"), max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
    )
    verba_ferramenta = models.DecimalField(
        _("Verba Ferramenta (R$)"), max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        verbose_name = _("Verba Mensal")
        verbose_name_plural = _("Verbas Mensais")
        unique_together = ["contrato", "ano", "mes"]
        ordering = ["-ano", "-mes"]

    def __str__(self):
        return f"{self.contrato.cm} — {self.mes:02d}/{self.ano}"

    @property
    def verba_total(self):
        return self.verba_epi + self.verba_consumo + self.verba_ferramenta

    def _soma_itens(self, classificacao):
        """Soma valor_total dos itens aprovados/entregues no mês."""
        from django.db.models import Sum

        total = ItemPedido.objects.filter(
            pedido__contrato=self.contrato,
            pedido__status__in=[
                Pedido.StatusChoices.APROVADO,
                Pedido.StatusChoices.ENTREGUE,
                Pedido.StatusChoices.RECEBIDO,
            ],
            pedido__data_pedido__year=self.ano,
            pedido__data_pedido__month=self.mes,
            material__classificacao=classificacao,
        ).aggregate(t=Sum("valor_total"))["t"]
        return total or Decimal("0.00")
    
    @property
    def compra_epi(self):
        return self._soma_itens(CategoriaMaterial.EPI)

    @property
    def compra_consumo(self):
        return self._soma_itens(CategoriaMaterial.CONSUMO)

    @property
    def compra_ferramenta(self):
        return self._soma_itens(CategoriaMaterial.FERRAMENTA)

    @property
    def compra_total(self):
        return self.compra_epi + self.compra_consumo + self.compra_ferramenta

    @property
    def saldo_epi(self):
        return self.verba_epi - self.compra_epi

    @property
    def saldo_consumo(self):
        return self.verba_consumo - self.compra_consumo

    @property
    def saldo_ferramenta(self):
        return self.verba_ferramenta - self.compra_ferramenta

    @property
    def saldo_total(self):
        return self.verba_total - self.compra_total



# ═════════════════════════════════════════════════════════════════════════════
# 4. PEDIDO DE MATERIAL
# ═════════════════════════════════════════════════════════════════════════════

class PedidoQuerySet(models.QuerySet):

    def visiveis_para(self, user):
        """Filtra pedidos conforme permissão do usuário."""
        from suprimentos.permissions import is_coordenador, is_comprador, is_gerencia
        if is_gerencia(user) or is_comprador(user):
            return self
        if is_coordenador(user):
            return self.filter(solicitante=user)
        return self.none()

class Pedido(TimestampedModel):
    """
    Pedido de material — Solicitante cria, Gerente aprova/reprova/devolve.
    Quando APROVADO, gera automaticamente uma SolicitacaoCompra.
    Workflow: Rascunho → Pendente ⇄ Revisão → Aprovado → (gera Solicitação)
              ou → Reprovado / Cancelado
    """

    class StatusChoices(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"
        PENDENTE = "PENDENTE", "Pendente de Aprovação"
        REVISAO = "REVISAO", "Em Revisão pelo Solicitante"
        APROVADO = "APROVADO", "Aprovado"
        REPROVADO = "REPROVADO", "Reprovado"
        ENTREGUE = "ENTREGUE", "Entregue"
        RECEBIDO = "RECEBIDO", "Recebido"
        SOLICITACAO_GERADA = "SOLICITACAO_GERADA", "Solicitação Gerada"
        CANCELADO = "CANCELADO", "Cancelado"

    # ── Identificação ────────────────────────────────────────────────────────
    numero = models.CharField(
        _("Nº Pedido"), max_length=30, unique=True, editable=False,
    )
    contrato = models.ForeignKey(
        Contrato, on_delete=models.PROTECT,
        related_name="pedidos", verbose_name=_("Contrato"),
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        verbose_name=_("Filial"), null=True, blank=True,
    )
    status = models.CharField(
        _("Status"), max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.RASCUNHO,
    )

    # ── Tipo de Obra ─────────────────────────────────────────────────────────
    tipo_obra = models.CharField(
        _("Tipo de Obra"), max_length=2,
        choices=TipoObra.choices,
        default=TipoObra.CM,
    )

    data_necessaria = models.DateField(
        _("Data Necessária para Entrega"),
        null=True, blank=True,
        help_text=_(
            "Data em que o material deve estar disponível no contrato."
        ),
    )

    # ── Responsáveis ─────────────────────────────────────────────────────────
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="pedidos_solicitados", verbose_name=_("Solicitante"),
    )
    aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="pedidos_aprovados", verbose_name=_("Aprovador"),
        null=True, blank=True,
        help_text=_("Gerente responsável pela aprovação."),
    )
    recebedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="pedidos_recebidos", verbose_name=_("Recebido por"),
        null=True, blank=True,
    )

    # ── Datas do Workflow ────────────────────────────────────────────────────
    data_pedido = models.DateTimeField(
        _("Data do Pedido"), auto_now_add=True,
    )
    data_aprovacao = models.DateTimeField(
        _("Data Aprovação"), null=True, blank=True,
    )
    data_entrega = models.DateField(
        _("Data Entrega"), null=True, blank=True,
    )
    data_recebimento = models.DateTimeField(
        _("Data Recebimento"), null=True, blank=True,
    )

    # ── Revisão ──────────────────────────────────────────────────────────────
    motivo_revisao = models.TextField(
        _("Motivo da Revisão/Devolução"), blank=True, default="",
        help_text=_(
            "Preenchido pelo Gerente ao devolver para revisão."
        ),
    )
    motivo_reprovacao = models.TextField(
        _("Motivo Reprovação"), blank=True, default="",
    )

    # ── Observações e Controle ───────────────────────────────────────────────
    observacao = models.TextField(
        _("Observação"), blank=True, default="",
    )
    estoque_processado = models.BooleanField(
        _("Estoque Processado"), default=False, editable=False,
        help_text=_("Indica se a entrada no estoque já foi gerada."),
    )

    # ── Vínculo com SolicitacaoCompra ────────────────────────────────────────
    solicitacao_gerada = models.OneToOneField(
        "SolicitacaoCompra", on_delete=models.SET_NULL,
        null=True, blank=True, editable=False,
        related_name="pedido_origem",
        verbose_name=_("Solicitação de Compra Gerada"),
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Pedido de Material")
        verbose_name_plural = _("Pedidos de Material")
        ordering = ["-data_pedido"]
        permissions = [
            ("pode_aprovar_pedido", "Pode aprovar pedidos de material"),
        ]

    def __str__(self):
        return f"Pedido {self.numero} — {self.contrato.cliente}"

    def get_absolute_url(self):
        return reverse("suprimentos:pedido_detalhe", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self._gerar_numero()
        super().save(*args, **kwargs)

    def _gerar_numero(self):
        import re
        from django.db import transaction
        
        hoje = timezone.now()
        prefix = f"PED-{hoje.strftime('%Y%m')}-"
        
        for tentativa in range(5):
            with transaction.atomic():
                ultimo = (
                    Pedido._base_manager
                    .select_for_update()
                    .filter(numero__startswith=prefix)
                    .order_by("-numero")
                    .first()
                )
                
                if ultimo:
                    match = re.search(r'-(\d+)$', ultimo.numero)
                    seq = int(match.group(1)) + 1 if match else 1
                else:
                    seq = 1
                
                numero_candidato = f"{prefix}{seq:04d}"
                
                if not Pedido._base_manager.filter(numero=numero_candidato).exists():
                    return numero_candidato
        
        return f"{prefix}{int(hoje.timestamp()) % 10000:04d}"


    @property
    def valor_total(self):
        from django.db.models import Sum

        return (
            self.itens.aggregate(t=Sum("valor_total"))["t"]
            or Decimal("0.00")
        )

    def totais_por_classificacao(self):
        from django.db.models import Sum

        qs = self.itens.values("material__classificacao").annotate(
            total=Sum("valor_total")
        )
        return {
            item["material__classificacao"]: item["total"] for item in qs
        }

    def verificar_verba(self):
        verba = self.contrato.verba_do_mes(
            self.data_pedido.year, self.data_pedido.month
        )
        totais = self.totais_por_classificacao()
        erros = []
        checks = [
            ("EPI", verba.saldo_epi),
            ("CONSUMO", verba.saldo_consumo),
            ("FERRAMENTA", verba.saldo_ferramenta),
        ]
        for cat, saldo in checks:
            pedido_val = totais.get(cat, Decimal("0.00"))
            if pedido_val > saldo:
                erros.append(
                    f"{cat}: pedido R$ {pedido_val:.2f} > "
                    f"saldo R$ {saldo:.2f}"
                )
        return len(erros) == 0, erros

    @transaction.atomic
    def gerar_solicitacao_compra(self, usuario, usar_novo_fluxo=True):
        from decimal import Decimal
        from django.core.exceptions import ValidationError

        if self.status != self.StatusChoices.APROVADO:
            raise ValidationError(
                f"Pedido {self.numero} precisa estar APROVADO para gerar "
                f"solicitação. Status atual: {self.get_status_display()}."
            )

        itens_pedido = list(self.itens.select_related("material").all())
        if not itens_pedido:
            raise ValidationError(
                f"Pedido {self.numero} não possui itens para gerar solicitação."
            )

        # ── Resumo dos itens (Pedido não tem mais esses campos) ──
        primeiro = itens_pedido[0]
        descricao_resumo = (
            f"{len(itens_pedido)} item(ns): "
            + ", ".join(
                f"{i.quantidade} {i.get_unidade_medida_display()} {i.material.descricao}"
                for i in itens_pedido[:3]
            )
            + ("..." if len(itens_pedido) > 3 else "")
        )
        qtd_total = sum((i.quantidade for i in itens_pedido), 0)

        # ═══════════════════════════════════════════════════════════
        # ✅ REAPROVEITAMENTO: já existe solicitação para este pedido?
        # ═══════════════════════════════════════════════════════════
        solicitacao_existente = SolicitacaoCompra.objects.filter(pedido=self).first()
        if solicitacao_existente:
            S = SolicitacaoCompra.StatusChoices
            status_valido = solicitacao_existente.status in {c[0] for c in S.choices}

            # Status FAZER_COTACAO (normal) OU status corrompido/órfão
            # (ex.: "PENDENTE_COTACAO" vindo do enum errado) → ressincroniza.
            pode_ressincronizar = (
                not status_valido
                or solicitacao_existente.status == S.FAZER_COTACAO
            )

            if pode_ressincronizar:
                # Se o status estava corrompido, normaliza para FAZER_COTACAO
                if solicitacao_existente.status != S.FAZER_COTACAO:
                    solicitacao_existente.status = S.FAZER_COTACAO

                # Atualiza o cabeçalho com os dados do pedido (possivelmente revisado)
                solicitacao_existente.filial = self.filial
                solicitacao_existente.solicitante = self.solicitante
                solicitacao_existente.contrato = self.contrato
                solicitacao_existente.tipo_obra = self.tipo_obra
                solicitacao_existente.descricao_material = descricao_resumo
                solicitacao_existente.quantidade = qtd_total
                solicitacao_existente.unidade_medida = primeiro.unidade_medida
                solicitacao_existente.tipo_insumo = primeiro.material.tipo
                solicitacao_existente.data_necessaria = self.data_necessaria
                solicitacao_existente.aprovador_inicial = self.aprovador
                solicitacao_existente.data_aprovacao_inicial = self.data_aprovacao
                solicitacao_existente.usa_novo_fluxo = usar_novo_fluxo
                solicitacao_existente.save()

                # Ressincroniza os itens com o pedido revisado
                itens_criados = 0
                if usar_novo_fluxo:
                    solicitacao_existente.itens.all().delete()
                    for item_pedido in itens_pedido:
                        if item_pedido.material_id is None:
                            raise ValidationError(
                                f"Item do Pedido {self.numero} sem Material vinculado."
                            )
                        ItemSolicitacao.objects.create(
                            solicitacao=solicitacao_existente,
                            item_pedido_origem=item_pedido,
                            material=item_pedido.material,
                            quantidade=item_pedido.quantidade,
                            valor_unitario_estimado=(
                                item_pedido.valor_unitario or Decimal("0.00")
                            ),
                            observacao=item_pedido.observacao or "",
                            status=ItemSolicitacao.StatusItem.PENDENTE_COTACAO,
                        )
                        itens_criados += 1
                descricao_hist = (
                    f"Solicitação de Compra {solicitacao_existente.numero} "
                    f"reaproveitada e ressincronizada ({itens_criados} item(ns))."
                )
            else:
                # Cotação realmente em andamento: não mexe nos itens.
                descricao_hist = (
                    f"Solicitação de Compra {solicitacao_existente.numero} "
                    f"reaproveitada (cotação em andamento — itens preservados)."
                )

            # Revincula e ajusta o status do pedido
            if self.solicitacao_gerada_id != solicitacao_existente.pk:
                self.solicitacao_gerada = solicitacao_existente
            self.status = self.StatusChoices.SOLICITACAO_GERADA
            self.save(update_fields=[
                "solicitacao_gerada", "status", "atualizado_em"
            ])

            try:
                HistoricoPedido.registrar(
                    pedido=self,
                    descricao=descricao_hist,
                    responsavel=usuario,
                    status_anterior=self.StatusChoices.APROVADO,
                    status_novo=self.StatusChoices.SOLICITACAO_GERADA,
                )
            except Exception:
                pass

            return solicitacao_existente


        # ═══════════════════════════════════════════════════════════
        # CRIAÇÃO NORMAL (primeira vez)
        # ═══════════════════════════════════════════════════════════
        status_inicial = SolicitacaoCompra.StatusChoices.FAZER_COTACAO

        solicitacao = SolicitacaoCompra.objects.create(
            pedido=self,
            filial=self.filial,
            solicitante=self.solicitante,
            contrato=self.contrato,
            tipo_obra=self.tipo_obra,
            descricao_material=descricao_resumo,
            quantidade=qtd_total,
            unidade_medida=primeiro.unidade_medida,
            tipo_insumo=primeiro.material.tipo,
            data_necessaria=self.data_necessaria,
            aprovador_inicial=self.aprovador,
            data_aprovacao_inicial=self.data_aprovacao,
            status=status_inicial,
            usa_novo_fluxo=usar_novo_fluxo,
            observacoes=f"Gerada automaticamente a partir do Pedido {self.numero}.",
        )

        itens_criados = 0
        if usar_novo_fluxo:
            for item_pedido in itens_pedido:
                if item_pedido.material_id is None:
                    raise ValidationError(
                        f"Item do Pedido {self.numero} sem Material vinculado."
                    )
                ItemSolicitacao.objects.create(
                    solicitacao=solicitacao,
                    item_pedido_origem=item_pedido,
                    material=item_pedido.material,
                    quantidade=item_pedido.quantidade,
                    valor_unitario_estimado=(
                        item_pedido.valor_unitario or Decimal("0.00")
                    ),
                    observacao=item_pedido.observacao or "",
                    status=ItemSolicitacao.StatusItem.PENDENTE_COTACAO,
                )
                itens_criados += 1

        self.solicitacao_gerada = solicitacao
        self.status = self.StatusChoices.SOLICITACAO_GERADA
        self.save(update_fields=[
            "solicitacao_gerada", "status", "atualizado_em"
        ])

        try:
            HistoricoPedido.registrar(
                pedido=self,
                descricao=(
                    f"Solicitação de Compra {solicitacao.numero} gerada "
                    f"({itens_criados} item(ns))."
                ),
                responsavel=usuario,
                status_anterior=self.StatusChoices.APROVADO,
                status_novo=self.StatusChoices.SOLICITACAO_GERADA,
            )
        except Exception:
            pass

        return solicitacao

# ═════════════════════════════════════════════════════════════════════════════
# 4b. ANEXOS DO PEDIDO
# ═════════════════════════════════════════════════════════════════════════════

class AnexoPedido(BaseAnexo):
    """Anexo vinculado a um Pedido de Material (com upload seguro)."""

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name="anexos", verbose_name=_("Pedido"),
    )

    # ── Upload seguro — Anexo ────────────────────────────────────────────────
    arquivo = models.FileField(
        upload_to=make_upload_path('suprimentos_anexos_pedido'),
        validators=[SecureFileValidator('suprimentos_anexos_pedido')],
        verbose_name='Arquivo',
    )

    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='anexos_pedido_enviados',
        verbose_name='Enviado por',
    )

    observacao = models.CharField(
        _("Observação"), max_length=255, blank=True, default="",
        help_text=_("Descrição opcional do anexo."),
    )
    
    class Meta(BaseAnexo.Meta):
        verbose_name = "Anexo do Pedido"
        verbose_name_plural = "Anexos dos Pedidos"
        permissions = [
            ("view_anexopedido_outros", "Pode ver anexos de pedidos de outros usuários"),
            ("download_anexopedido", "Pode baixar anexos de pedidos"),
        ]
        ordering = ["-criado_em"]

    def __str__(self):      
        return self.nome_arquivo
    
    # ── Ciclo de vida ────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        from core.upload import delete_old_file, sanitize_image

        if self.pk:
            delete_old_file(self, "arquivo")

        super().save(*args, **kwargs)

        # Se o anexo for imagem, sanitiza (strip EXIF, recodifica)
        if self.arquivo and self.arquivo.name:
            ext = self.arquivo.name.rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "png", "webp"):
                sanitize_image(self.arquivo.path)

    def delete(self, *args, **kwargs):
        from core.upload import safe_delete_file

        safe_delete_file(self, "arquivo")
        super().delete(*args, **kwargs)

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def nome_arquivo(self):
        return os.path.basename(self.arquivo.name) if self.arquivo else ''

    @property
    def extensao(self):
        nome = self.nome_arquivo
        return nome.rsplit(".", 1)[-1].lower() if "." in nome else ""

    @property
    def is_imagem(self):
        return self.extensao in ("jpg", "jpeg", "png", "gif", "webp", "bmp")

    @property
    def is_pdf(self):
        return self.extensao == "pdf"


# ═════════════════════════════════════════════════════════════════════════════
# 4c. HISTÓRICO DO PEDIDO
# ═════════════════════════════════════════════════════════════════════════════

class HistoricoPedido(BaseHistorico):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="historico"
    )
    versao = models.PositiveIntegerField(_("Versão"))
    descricao = models.TextField(_("Descrição das Alterações"))
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="historicos_pedido",
    )
    status_anterior = models.CharField(_("Status Anterior"), max_length=25, blank=True)
    status_novo = models.CharField(_("Status Novo"), max_length=25, blank=True)


    class Meta(BaseHistorico.Meta):
        verbose_name = _("Histórico do Pedido")
        verbose_name_plural = _("Histórico dos Pedidos")
        ordering = ["-versao"]

    def __str__(self):
        return f"v{self.versao} — {self.pedido.numero}"

    @classmethod
    def registrar(cls, pedido, descricao, responsavel, status_anterior="", status_novo=""):
        ultima_versao = (
            cls.objects.filter(pedido=pedido)
            .order_by("-versao")
            .values_list("versao", flat=True)
            .first()
            or 0
        )
        return cls.objects.create(
            pedido=pedido,
            versao=ultima_versao + 1,
            descricao=descricao,
            responsavel=responsavel,
            status_anterior=status_anterior,
            status_novo=status_novo,
        )


# ═════════════════════════════════════════════════════════════════════════════
# 5. ITEM DO PEDIDO
# ═════════════════════════════════════════════════════════════════════════════

class ItemPedido(models.Model):
    """Linha do pedido: material + quantidade + valor."""

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name="itens", verbose_name=_("Pedido"),
    )
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name="itens_pedido", verbose_name=_("Material"),
    )
    quantidade = models.PositiveIntegerField(
        _("Quantidade"), validators=[MinValueValidator(1)],
    )
    unidade_medida = models.CharField(
        _("Unidade de Medida"), max_length=20,
        choices=UnidadeMedida.choices,
        default=UnidadeMedida.UNID,
    )
    valor_unitario = models.DecimalField(
        _("Valor Unitário (R$)"), max_digits=10, decimal_places=2,
    )
    valor_total = models.DecimalField(
        _("Valor Total (R$)"), max_digits=12, decimal_places=2,
        editable=False, default=Decimal("0.00"),
    )
    observacao = models.CharField(
        _("Observação"), max_length=255, blank=True, default="",
    )

    # ── Campos tributação ────────────────────────────────────────────────────
    custo_real = models.DecimalField(
        _("Custo Real (R$)"), max_digits=14, decimal_places=2,
        default=Decimal("0.00"), editable=False,
    )
    total_creditos = models.DecimalField(
        _("Créditos Fiscais (R$)"), max_digits=14, decimal_places=2,
        default=Decimal("0.00"), editable=False,
    )
    total_impostos = models.DecimalField(
        _("Total Impostos (R$)"), max_digits=14, decimal_places=2,
        default=Decimal("0.00"), editable=False,
    )

    def calcular_impostos(self):
        valor = self.quantidade * self.valor_unitario
        return self.material.calcular_custo_compra(valor, self.quantidade)

    def save(self, *args, **kwargs):
        self.valor_total = self.quantidade * self.valor_unitario
        # Se não vier unidade, herda do Material (UX amigável)
        if not self.unidade_medida and self.material_id:
            self.unidade_medida = self.material.unidade
        try:
            calc = self.calcular_impostos()
            self.total_impostos = calc.get("total_impostos", Decimal("0.00"))
            self.total_creditos = calc.get("total_creditos", Decimal("0.00"))
            self.custo_real = calc.get("custo_real", Decimal("0.00"))
        except Exception:
            self.total_impostos = Decimal("0.00")
            self.total_creditos = Decimal("0.00")
            self.custo_real = Decimal("0.00")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Item do Pedido")
        verbose_name_plural = _("Itens do Pedido")
        ordering = ["material__classificacao", "material__tipo"]

    def __str__(self):
        unidade = self.get_unidade_medida_display() if self.unidade_medida else ""
        return f"{self.quantidade}x {self.material.descricao}"


# ═════════════════════════════════════════════════════════════════════════════
# 6. SOLICITAÇÃO DE COMPRA — WORKFLOW PÓS-APROVAÇÃO
# ═════════════════════════════════════════════════════════════════════════════

class SolicitacaoCompra(TimestampedModel):
    """
    Fluxo:
      APROVAR PEDIDO → SOLICITAÇÃO DE COTAÇÃO → APROVAR COTAÇÃO →
      MONTAR PEDIDO DE COMPRA → ACOMPANHAR ENTREGA → FINALIZAR
    """

    class StatusChoices(models.TextChoices):
        # 1) Cotação (NxN) — supr. lança preços por fornecedor
        FAZER_COTACAO   = "FAZER_COTACAO",   "Fazer Cotação"
        COTACAO_ENVIADA = "COTACAO_ENVIADA", "Cotação Enviada"
        # 2) Aprovação da cotação (gerente + verba)
        EM_APROVACAO    = "EM_APROVACAO",    "Em Aprovação"
        APROVADO        = "APROVADO",        "Aprovado"
        # 3) Montar Pedido de Compra
        ENVIAR_PEDIDO   = "ENVIAR_PEDIDO",   "Pronto p/ Pedido de Compra"
        PEDIDO_GERADO   = "PEDIDO_GERADO",   "Pedido de Compra Gerado"
        # 4) Pós-compra
        EM_ENTREGA      = "EM_ENTREGA",      "Acompanhar Entrega"
        FINALIZADO      = "FINALIZADO",      "Finalizado"
        CANCELADO       = "CANCELADO",       "Cancelado"

    # Novo campo (substitui numero_pedido)
    numero_pedido = models.CharField(
        _("Nº do Pedido (Externo)"),
        max_length=50,
        blank=True,
        default="",
        help_text=_(
            "Nº do pedido no sistema externo. "
            "DEPRECATED na SolicitacaoCompra — usar PedidoCompra.numero_pedido."
        ),
    )

    # Flag para indicar que esta solicitação já usa o novo fluxo
    usa_novo_fluxo = models.BooleanField(
        _("Usa novo fluxo (v2)"),
        default=False,
        help_text=_(
            "Marca se esta solicitação usa o fluxo com ItemSolicitacao+Cotacao+PedidoCompra."
        ),
    )

    # ── Identificação ────────────────────────────────────────────────────────
    pedido = models.OneToOneField(
        "suprimentos.Pedido",
        on_delete=models.PROTECT,
        related_name="solicitacao",
    )

    numero = models.CharField(
        _("Nº Solicitação"), max_length=30, unique=True, editable=False,
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        verbose_name=_("Filial"), null=True, blank=True,
    )
    status = models.CharField(
        _("Status"), max_length=25,
        choices=StatusChoices.choices,
        default=StatusChoices.FAZER_COTACAO,
    )

    # ── Dados herdados do Pedido ─────────────────────────────────────────────
    tipo_obra = models.CharField(
        _("Tipo de Obra"), max_length=2,
        choices=TipoObra.choices,
    )
    contrato = models.ForeignKey(
        Contrato, on_delete=models.PROTECT,
        related_name="solicitacoes_compra",
        verbose_name=_("Obra (CM / CR / VE)"),
    )
    descricao_material = models.TextField(_("Descrição do Material"))
    quantidade = models.DecimalField(
        _("Quantidade"), max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    unidade_medida = models.CharField(
        _("Unidade de Medida"), max_length=20,
        choices=UnidadeMedida.choices,
        default=UnidadeMedida.UNID,
    )
    tipo_insumo = models.CharField(
        _("Tipo de Insumo"), max_length=30,
        choices=TipoMaterial.choices,
        blank=True, default="",
    )
    data_necessaria = models.DateField(
        _("Data Necessária para Entrega"), null=True, blank=True,
    )

    # ── Responsáveis ─────────────────────────────────────────────────────────
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="solicitacoes_compra",
        verbose_name=_("Solicitante"),
    )
    aprovador_inicial = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="solicitacoes_aprovador_inicial",
        verbose_name=_("Aprovador (Gerente)"),
        null=True, blank=True,
        help_text=_("Gerente que aprovou o pedido original."),
    )
    comprador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="solicitacoes_comprador",
        verbose_name=_("Comprador Responsável"),
        null=True, blank=True,
        help_text=_(
            "Profissional de Suprimentos responsável pela cotação e compra."
        ),
    )
    aprovador_cotacao = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="solicitacoes_aprovador_cotacao",
        verbose_name=_("Aprovador da Cotação"),
        null=True, blank=True,
    )
    aprovador_pedido = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="solicitacoes_aprovador_pedido",
        verbose_name=_("Aprovador do Pedido"),
        null=True, blank=True,
    )

    # ── Etapa 1 — Aprovação Inicial ──────────────────────────────────────────
    data_aprovacao_inicial = models.DateTimeField(
        _("Data Aprovação Inicial"), null=True, blank=True,
    )

    # ── Etapa 2 — Cotação (Comprador) ────────────────────────────────────────
    data_cotacao = models.DateField(
        _("Data da Cotação"), null=True, blank=True,
    )
    numero_cotacao = models.CharField(
        _("Nº da Cotação"), max_length=50, blank=True, default="",
    )
    cnpj_compra = models.CharField(
        _("CNPJ para Compra"), max_length=18, blank=True, default="",
    )
    tipo_nota_fiscal = models.CharField(
        _("Tipo de Nota Fiscal"), max_length=20,
        choices=TipoNotaFiscal.choices,
        blank=True, default="",
    )

    # ── Etapa 3 — Validação da Cotação ───────────────────────────────────────
    data_validacao_cotacao = models.DateField(
        _("Data da Validação"), null=True, blank=True,
    )

    # ── Etapa 4 — Pedido ───────────────────────────────────────────
    data_criacao_pedido = models.DateField(
        _("Data Criação do Pedido"), null=True, blank=True,
    )
    numero_pedido = models.CharField(
        _("Nº do Pedido"), max_length=50, blank=True, default="",
    )
    fornecedor = models.ForeignKey(
        Parceiro, on_delete=models.SET_NULL,
        related_name="solicitacoes_fornecidas",
        verbose_name=_("Fornecedor"), null=True, blank=True,
    )
    valor_pedido = models.DecimalField(
        _("Valor do Pedido (R$)"), max_digits=14, decimal_places=2,
        null=True, blank=True,
    )

    # ── Etapa 5 — Aprovação do Pedido ────────────────────────────────────────
    data_aprovacao_pedido = models.DateField(
        _("Data Aprovação do Pedido"), null=True, blank=True,
    )

    # ── Etapa 6 — Envio ao Fornecedor ────────────────────────────────────────
    data_envio_fornecedor = models.DateField(
        _("Data Envio ao Fornecedor"), null=True, blank=True,
    )

    # ── Etapa 7 — Entrega ────────────────────────────────────────────────────
    data_prevista_entrega = models.DateField(
        _("Data Prevista de Entrega"), null=True, blank=True,
    )
    data_entrega_efetiva = models.DateField(
        _("Data de Entrega Efetiva"), null=True, blank=True,
        help_text=_(
            "Obtida via planilha de rotas do motorista."
        ),
    )

    # ── Etapa 8 — Encerramento ───────────────────────────────────────────────
    numero_nota_fiscal = models.CharField(
        _("Nº da Nota Fiscal"), max_length=50, blank=True, default="",
    )

    # ── Observações e Cancelamento ───────────────────────────────────────────
    observacoes = models.TextField(
        _("Observações"), blank=True, default="",
        help_text=_(
            "Registro de informações relevantes sobre o processo."
        ),
    )
    motivo_cancelamento = models.TextField(
        _("Motivo do Cancelamento"), blank=True, default="",
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    criado_em = models.DateTimeField(_("Criado em"), auto_now_add=True)
    atualizado_em = models.DateTimeField(_("Atualizado em"), auto_now=True)

    objects = FilialManager()

    class Meta:
        verbose_name = _("Solicitação de Compra")
        verbose_name_plural = _("Solicitações de Compra")
        ordering = ["-criado_em"]
        permissions = [
            ("pode_executar_cotacao", "Pode executar cotações de compra"),
            ("pode_montar_pc", "Pode montar pedido de compra"),
            ("pode_enviar_pc", "Pode enviar pedido de compra"),
            ("pode_aprovar_pc", "Pode aprovar pedido de compra"),
            ("pode_entregar_pc", "Pode entregar pedido de compra"),
            ("pode_concluir_pc", "Pode concluir pedido de compra"),
            ("pode_cancelar_pc", "Pode cancelar pedido de compra"),
        ]

    def __str__(self):
        return f"SOL-{self.numero} — {self.descricao_material[:50]}"

    def get_absolute_url(self):
        return reverse(
            "suprimentos:solicitacao_detalhe", kwargs={"pk": self.pk}
        )

    def save(self, *args, **kwargs):
        valores_validos = {c[0] for c in self.StatusChoices.choices}
        if self.status not in valores_validos:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f"Status inválido em SolicitacaoCompra: '{self.status}'. "
                f"Válidos: {sorted(valores_validos)}"
            )
        super().save(*args, **kwargs)
        
        if not self.numero:
            hoje = timezone.now()
            prefix = f"SOL-{hoje.strftime('%Y%m')}"
            ultimo = (
                SolicitacaoCompra.objects.filter(numero__startswith=prefix)
                .order_by("-numero")
                .first()
            )
            seq = int(ultimo.numero.split("-")[-1]) + 1 if ultimo else 1
            self.numero = f"{prefix}-{seq:04d}"
        super().save(*args, **kwargs)

    # ── Verificação de Verba ─────────────────────────────────────────────────

    def verificar_verba(self):
        if not self.valor_pedido:
            return True, "Valor do pedido ainda não definido."

        ano = (
            self.data_necessaria.year
            if self.data_necessaria
            else timezone.now().year
        )
        mes = (
            self.data_necessaria.month
            if self.data_necessaria
            else timezone.now().month
        )
        verba = self.contrato.verba_do_mes(ano, mes)

        campo_saldo = "saldo_consumo"
        cat_label = "Consumo"
        campo_verba = "verba_consumo"

        if self.tipo_insumo in ("EPI", "CREME"):
            campo_saldo = "saldo_epi"
            campo_verba = "verba_epi"
            cat_label = "EPI"

        saldo = getattr(verba, campo_saldo, Decimal("0.00"))
        if self.valor_pedido > saldo:
            return False, (
                f"⚠️ Valor R$ {self.valor_pedido:.2f} excede o saldo de "
                f"{cat_label}: R$ {saldo:.2f} "
                f"(Verba: R$ {getattr(verba, campo_verba):.2f})"
            )
        return True, "Dentro da verba."
    
    def sincronizar_status_entrega(self, responsavel=None):
        """
        Sincroniza o status da solicitação com base nos PCs:
        - todos RECEBIDO  → FINALIZADO
        - algum em curso   → EM_ENTREGA
        Idempotente: só grava se houver mudança real.
        """
        PC = PedidoCompra.StatusPC
        S = self.StatusChoices

        pcs = self.pedidos_compra.exclude(status=PC.CANCELADO)
        if not pcs.exists():
            return

        todos_recebidos = not pcs.exclude(status=PC.RECEBIDO).exists()

        if todos_recebidos:
            novo = S.FINALIZADO
        else:
            # algum PC já saiu de EMITIDO (foi enviado/parcial/entregue)
            em_andamento = pcs.exclude(status=PC.EMITIDO).exists()
            novo = S.EM_ENTREGA if em_andamento else S.PEDIDO_GERADO

        if self.status != novo:
            anterior = self.status
            self.status = novo
            if novo == S.FINALIZADO:
                self.data_entrega_efetiva = timezone.now().date()
                self.save(update_fields=["status", "data_entrega_efetiva", "atualizado_em"])
            else:
                self.save(update_fields=["status", "atualizado_em"])
            _registrar_historico(  # mova esse helper p/ um utils se preferir
                HistoricoSolicitacao.registrar,
                solicitacao=self,
                descricao=f"Status sincronizado pelos PCs: {anterior} → {novo}",
                responsavel=responsavel,
                status_anterior=anterior,
                status_novo=novo,
            )

    # ── Properties ───────────────────────────────────────────────────────────
    @property
    def anexos_do_pedido(self):
        """Acesso read-only aos anexos originais do pedido."""
        return self.pedido.anexos.all()

    @property
    def status_badge_class(self):
        S = self.StatusChoices
        mapa = {
            S.FAZER_COTACAO:   "info",
            S.COTACAO_ENVIADA: "warning text-dark",
            S.EM_APROVACAO:    "warning text-dark",
            S.APROVADO:        "primary",
            S.ENVIAR_PEDIDO:   "primary",
            S.PEDIDO_GERADO:   "primary",
            S.EM_ENTREGA:      "secondary",
            S.FINALIZADO:      "success",
            S.CANCELADO:       "dark",
        }
        return mapa.get(self.status, "secondary")

    @property
    def etapa_atual(self):
        S = self.StatusChoices
        mapa = {
            S.FAZER_COTACAO:   1,
            S.COTACAO_ENVIADA: 2,
            S.EM_APROVACAO:    3,
            S.APROVADO:        4,
            S.PEDIDO_GERADO:   4,
            S.ENVIAR_PEDIDO:   5,
            S.EM_ENTREGA:      7,
            S.FINALIZADO:      8,
            S.CANCELADO:       0,
        }
        etapa = mapa.get(self.status, 1)
        if self.status == S.EM_ENTREGA and self.data_entrega_efetiva:
            etapa = 7
        return etapa


    @property
    def dias_em_aberto(self):
        if self.status in (self.StatusChoices.FINALIZADO, self.StatusChoices.CANCELADO):
            return 0
        delta = timezone.now().date() - self.criado_em.date()
        return delta.days

    @property
    def pode_cancelar(self):
        return self.status not in (
            self.StatusChoices.FINALIZADO,
            self.StatusChoices.CANCELADO,
        )
    
    @property
    def todos_itens_cotados(self) -> bool:
        """True se todos os itens têm ao menos 1 cotação."""
        itens = self.itens.all()
        if not itens:
            return False
        return all(item.tem_cotacoes for item in itens)

    @property
    def valor_cotado(self):
        """Soma do menor total de cada item (menor preço cotado)."""
        return sum(
            (it.menor_cotacao.valor_total
             for it in self.itens.all() if it.menor_cotacao),
            Decimal("0.00"),
        )

    @property
    def valor_estimado(self):
        """
        Soma do valor estimado dos itens.
        Se o item não tiver valor_estimado próprio, usa a menor cotação
        como referência (fallback), para nunca zerar à toa.
        """
        total = Decimal("0.00")
        for it in self.itens.all():
            est = getattr(it, "valor_estimado", None)
            if est:
                total += est
            elif it.menor_cotacao:
                total += it.menor_cotacao.valor_total
        return total

# ═════════════════════════════════════════════════════════════════════════════
# 6b. ANEXOS DA SOLICITAÇÃO
# ═════════════════════════════════════════════════════════════════════════════

class AnexoSolicitacao(BaseAnexo):
    """Anexo vinculado a uma Solicitação de Compra (com upload seguro)."""

    solicitacao = models.ForeignKey(
        'SolicitacaoCompra',
        on_delete=models.CASCADE,
        related_name='anexos',
        verbose_name='Solicitação',
    )
    arquivo = models.FileField(
        upload_to=make_upload_path('suprimentos_anexos_solicitacao'),
        validators=[SecureFileValidator('suprimentos_anexos_solicitacao')],
        verbose_name='Arquivo',
    )
    tipo_documento = models.CharField(
        max_length=30,
        choices=[
            ("COTACAO", "Cotação"),
            ("PEDIDO", "Pedido"),
            ("NOTA_FISCAL", "Nota Fiscal"),
            ("COMPROVANTE", "Comprovante de Entrega"),
            ("OUTRO", "Outro"),
        ],
        default="OUTRO",
    )
    confidencial = models.BooleanField(
        default=False,
        help_text="Se marcado, apenas Gerência pode visualizar.",
    )

    descricao = models.CharField(
        _("Descrição"), max_length=255, blank=True, default="",
    )
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='anexos_solicitacao_enviados',
        verbose_name='Enviado por',
    )

    criado_em = models.DateTimeField(_("Data"), auto_now_add=True)

    class Meta(BaseAnexo.Meta):   
        verbose_name = "Anexo da Solicitação"
        verbose_name_plural = "Anexos das Solicitações"
        permissions = [
            ("view_anexosolicitacao_confidencial", "Pode ver anexos confidenciais"),
            ("download_anexosolicitacao", "Pode baixar anexos de solicitações"),
        ]


    def save(self, *args, **kwargs):
        from core.upload import delete_old_file, sanitize_image
        if self.pk:
            delete_old_file(self, "arquivo")
        super().save(*args, **kwargs)
        if self.arquivo and self.arquivo.name:
            ext = self.arquivo.name.rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "png", "webp"):
                sanitize_image(self.arquivo.path)

    def delete(self, *args, **kwargs):
        from core.upload import safe_delete_file
        safe_delete_file(self, "arquivo")
        super().delete(*args, **kwargs)


class EntregaAnexo(models.Model):
    """Anexos (notas fiscais / comprovantes) de cada recebimento do PC."""
    pedido_compra = models.ForeignKey(
        "PedidoCompra",
        on_delete=models.CASCADE,
        related_name="anexos_entrega",   # usado nas views: pc.anexos_entrega.all()
    )
    arquivo = models.FileField(upload_to="entregas/%Y/%m/")
    nota_fiscal = models.CharField("Nota Fiscal", max_length=60, blank=True)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="anexos_entrega_enviados",
    )
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enviado_em"]
        verbose_name = "Anexo de Entrega"
        verbose_name_plural = "Anexos de Entrega"

    def __str__(self):
        return f"Anexo PC {self.pedido_compra_id} — NF {self.nota_fiscal or 's/ NF'}"


class HistoricoSolicitacao(BaseHistorico):
    """Registro de cada alteração na solicitação (versionamento)."""

    solicitacao = models.ForeignKey(
        'SolicitacaoCompra', on_delete=models.CASCADE,
        related_name="historico", verbose_name=_("Solicitação"),
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="historicos_solicitacao", verbose_name=_("Usuário"),
    )
    versao = models.PositiveIntegerField(_("Versão"))
    descricao = models.TextField(_("Descrição das Alterações"))
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="historicos_solic_responsavel",
        verbose_name=_("Responsável"),
    )
    status_anterior = models.CharField(_("Status Anterior"), max_length=25, blank=True, default="")
    status_novo = models.CharField(_("Status Novo"), max_length=25, blank=True, default="")

    class Meta(BaseHistorico.Meta):   
        verbose_name = _("Histórico da Solicitação")
        verbose_name_plural = _("Histórico das Solicitações")
        ordering = ["-versao"]
        

    def __str__(self):
        return f"v{self.versao} — {self.descricao[:60]}"

    @classmethod
    def registrar(cls, solicitacao, descricao, responsavel, status_anterior="", status_novo=""):
        ultima_versao = (
            cls.objects.filter(solicitacao=solicitacao)
            .order_by("-versao")
            .values_list("versao", flat=True)
            .first()
            or 0
        )
        return cls.objects.create(
            solicitacao=solicitacao,
            usuario=responsavel,
            versao=ultima_versao + 1,
            descricao=descricao,
            responsavel=responsavel,
            status_anterior=status_anterior,
            status_novo=status_novo,
        )

# ═════════════════════════════════════════════════════════════════════════════
# 7. ESTOQUE DE CONSUMO
# ═════════════════════════════════════════════════════════════════════════════

class EstoqueConsumo(models.Model):
    """Movimentação de estoque para materiais de consumo."""

    class TipoMovimento(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SAIDA = "SAIDA", "Saída"
        AJUSTE = "AJUSTE", "Ajuste"

    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name="movimentacoes_consumo",
        verbose_name=_("Material"),
    )
    contrato = models.ForeignKey(
        Contrato, on_delete=models.PROTECT,
        related_name="estoque_consumo",
        verbose_name=_("Contrato"),
    )
    tipo = models.CharField(
        _("Tipo"), max_length=10, choices=TipoMovimento.choices,
    )
    quantidade = models.IntegerField(_("Quantidade"))
    pedido = models.ForeignKey(
        Pedido, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="movimentacoes_estoque",
        verbose_name=_("Pedido Origem"),
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        verbose_name=_("Responsável"),
    )
    justificativa = models.CharField(
        _("Justificativa"), max_length=255, blank=True, default="",
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT, verbose_name=_("Filial"),
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = FilialManager()

    class Meta:
        verbose_name = _("Movimentação de Estoque (Consumo)")
        verbose_name_plural = _("Movimentações de Estoque (Consumo)")
        ordering = ["-criado_em"]

    def __str__(self):
        return (
            f"{self.get_tipo_display()} - "
            f"{self.material.descricao} ({self.quantidade})"
        )

    @classmethod
    def saldo_material(cls, material_id, contrato_id, filial_id):
        from django.db.models import Q, Sum

        resultado = cls.objects.filter(
            material_id=material_id,
            contrato_id=contrato_id,
            filial_id=filial_id,
        ).aggregate(
            entradas=Sum("quantidade", filter=Q(tipo="ENTRADA"), default=0),
            saidas=Sum("quantidade", filter=Q(tipo="SAIDA"), default=0),
        )
        return resultado["entradas"] - resultado["saidas"]

    @classmethod
    def saldo_por_contrato(cls, contrato_id, filial_id):
        from django.db.models import Q, Sum

        return (
            cls.objects.filter(
                contrato_id=contrato_id,
                filial_id=filial_id,
            )
            .values(
                "material__id", "material__descricao", "material__unidade",
            )
            .annotate(
                entradas=Sum(
                    "quantidade", filter=Q(tipo="ENTRADA"), default=0,
                ),
                saidas=Sum(
                    "quantidade", filter=Q(tipo="SAIDA"), default=0,
                ),
            )
            .order_by("material__descricao")
        )

# ═════════════════════════════════════════════════════════════════════════════
# 8. ITEM DA SOLICITAÇÃO DE COMPRA (NOVO — Fase 1)
# ═════════════════════════════════════════════════════════════════════════════

class ItemSolicitacao(TimestampedModel):
    """
    Linha individual da Solicitação de Compra.
    Cada ItemPedido aprovado gera 1 ItemSolicitacao automaticamente.
    Recebe múltiplas Cotacoes (uma por fornecedor) e tem 1 escolhida.
    """

    class StatusItem(models.TextChoices):
        PENDENTE_COTACAO = "PENDENTE_COTACAO", "Pendente de Cotação"
        COTADO = "COTADO", "Cotado (aguardando aprovação)"
        APROVADO = "APROVADO", "Aprovado"
        REPROVADO = "REPROVADO", "Reprovado"
        CANCELADO = "CANCELADO", "Cancelado"

    solicitacao = models.ForeignKey(
        SolicitacaoCompra,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name=_("Solicitação de Compra"),
    )
    item_pedido_origem = models.ForeignKey(
        ItemPedido,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="itens_solicitacao_gerados",
        verbose_name=_("Item do Pedido (Origem)"),
        help_text=_("Rastreabilidade: ItemPedido que originou esta linha."),
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="itens_solicitacao",
        verbose_name=_("Material"),
    )
    quantidade = models.DecimalField(
        _("Quantidade"),
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    valor_unitario_estimado = models.DecimalField(
        _("Valor Unitário Estimado (R$)"),
        max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Valor de referência herdado do ItemPedido."),
    )
    observacao = models.CharField(
        _("Observação"),
        max_length=255, blank=True, default="",
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=StatusItem.choices,
        default=StatusItem.PENDENTE_COTACAO,
    )
    cotacao_escolhida = models.ForeignKey(
        "Cotacao",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="itens_que_escolheram",
        verbose_name=_("Cotação Escolhida"),
        help_text=_("Cotação aprovada pelo gerente para este item."),
    )
    motivo_reprovacao = models.TextField(
        _("Motivo Reprovação"),
        blank=True, default="",
    )

    class Meta:
        verbose_name = _("Item da Solicitação")
        verbose_name_plural = _("Itens da Solicitação")
        ordering = ["material__classificacao", "material__descricao"]
        indexes = [
            models.Index(fields=["solicitacao", "status"]),
            models.Index(fields=["material"]),
        ]

    def __str__(self):
        return f"{self.quantidade}x {self.material.descricao} (Sol. {self.solicitacao.numero})"

    @property
    def valor_total_estimado(self) -> Decimal:
        """Valor total estimado (referência do pedido original)."""
        return (self.quantidade * self.valor_unitario_estimado).quantize(Decimal("0.01"))

    @property
    def total_cotacoes(self) -> int:
        return self.cotacoes.count()

    @property
    def menor_cotacao(self):
        """Retorna a cotação de menor valor unitário (sugestão automática)."""
        return self.cotacoes.order_by("valor_unitario").first()

    @property
    def tem_cotacoes(self) -> bool:
        return self.cotacoes.exists()
    
    @property
    def tem_cotacao(self):
        return self.cotacoes.exists()


# ═════════════════════════════════════════════════════════════════════════════
# 9. COTAÇÃO (NOVO — Fase 1)
# ═════════════════════════════════════════════════════════════════════════════

class Cotacao(TimestampedModel):
    """
    Cotação de um fornecedor para um ItemSolicitacao específico.
    Múltiplas cotações por item permitem comparativo de preços.
    """

    item_solicitacao = models.ForeignKey(
        ItemSolicitacao,
        on_delete=models.CASCADE,
        related_name="cotacoes",
        verbose_name=_("Item da Solicitação"),
    )
    fornecedor = models.ForeignKey(
        Parceiro,
        on_delete=models.PROTECT,
        limit_choices_to={"eh_fornecedor": True, "ativo": True},
        related_name="cotacoes_realizadas",
        verbose_name=_("Fornecedor"),
    )
    valor_unitario = models.DecimalField(
        _("Valor Unitário (R$)"),
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    prazo_entrega_dias = models.PositiveIntegerField(
        _("Prazo de Entrega (dias)"),
        null=True, blank=True,
        help_text=_("Prazo prometido pelo fornecedor em dias corridos."),
    )
    condicoes_pagamento = models.CharField(
        _("Condições de Pagamento"),
        max_length=100, blank=True, default="",
        help_text=_("Ex.: 28/35/42 dias, à vista, boleto 30d..."),
    )
    validade_cotacao = models.DateField(
        _("Validade da Cotação"),
        null=True, blank=True,
    )
    observacoes = models.TextField(
        _("Observações"),
        blank=True, default="",
    )
    anexo_cotacao = models.FileField(
        upload_to="cotacoes/%Y/%m/",
        null=True, blank=True,
        verbose_name=_("Anexo (PDF da cotação)"),
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cotacoes_criadas",
        verbose_name=_("Criado por"),
    )

    class Meta:
        verbose_name = _("Cotação")
        verbose_name_plural = _("Cotações")
        ordering = ["item_solicitacao", "valor_unitario"]
        constraints = [
            models.UniqueConstraint(
                fields=["item_solicitacao", "fornecedor"],
                name="unique_cotacao_item_fornecedor",
                violation_error_message=_(
                    "Já existe uma cotação deste fornecedor para este item."
                ),
            ),
        ]
        indexes = [
            models.Index(fields=["item_solicitacao", "valor_unitario"]),
            models.Index(fields=["fornecedor"]),
        ]
        permissions = [
            ("pode_cotar", "Pode lançar cotações"),
            ("pode_aprovar_cotacao", "Pode aprovar cotações"),
        ]


    def __str__(self):
        return (
            f"{self.fornecedor.nome_fantasia} — "
            f"R$ {self.valor_unitario:.2f} "
            f"({self.item_solicitacao.material.descricao[:30]})"
        )

    @property
    def valor_total(self) -> Decimal:
        """Valor total da cotação (qtd × unitário)."""
        return (
            self.item_solicitacao.quantidade * self.valor_unitario
        ).quantize(Decimal("0.01"))

    @property
    def is_menor_preco(self) -> bool:
        """Retorna True se esta é a cotação de menor preço do item."""
        menor = self.item_solicitacao.menor_cotacao
        return menor and menor.pk == self.pk

    @property
    def is_escolhida(self) -> bool:
        """DEPRECATED na Interpretação 2 — sempre False."""
        return False


# ═════════════════════════════════════════════════════════════════════════════
# 10. PEDIDO DE COMPRA (NOVO — Fase 1)
# ═════════════════════════════════════════════════════════════════════════════

class PedidoCompra(TimestampedModel):
    """
    Pedido de Compra emitido para um fornecedor específico.
    Uma SolicitacaoCompra pode gerar N PedidosCompra (1 por fornecedor).
    """

    class StatusPC(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"
        EMITIDO = "EMITIDO", "Emitido"
        ENVIADO_FORNECEDOR = "ENVIADO_FORNECEDOR", "Enviado ao Fornecedor"
        ENTREGA_PARCIAL    = "ENTREGA_PARCIAL", "Entrega Parcial"
        ENTREGUE = "ENTREGUE", "Entregue"
        RECEBIDO = "RECEBIDO", "Recebido"
        CANCELADO = "CANCELADO", "Cancelado"

    # ── Identificação ────────────────────────────────────────────────────────
    numero = models.CharField(
        _("Nº Interno"),
        max_length=30, unique=True, editable=False,
        help_text=_("Numeração interna automática (PC-AAAAMM-NNNN)."),
    )
    numero_pedido = models.CharField(
        _("Nº do Pedido (Externo)"),
        max_length=50, blank=True, default="",
        help_text=_("Nº do PC no sistema externo, preenchido pelo comprador."),
    )
    solicitacao = models.ForeignKey(
        SolicitacaoCompra,
        on_delete=models.PROTECT,
        related_name="pedidos_compra",
        verbose_name=_("Solicitação de Compra"),
    )
    fornecedor = models.ForeignKey(
        Parceiro,
        on_delete=models.PROTECT,
        limit_choices_to={"eh_fornecedor": True},
        related_name="pedidos_compra_recebidos",
        verbose_name=_("Fornecedor"),
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="pedidos_compra",
        verbose_name=_("Filial"),
        null=True, blank=True,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=StatusPC.choices,
        default=StatusPC.RASCUNHO,
    )

    # ── Datas ────────────────────────────────────────────────────────────────
    data_emissao = models.DateField(
        _("Data de Emissão"), null=True, blank=True,
    )
    data_envio = models.DateField(
        _("Data de Envio ao Fornecedor"), null=True, blank=True,
    )
    data_entrega_prevista = models.DateField(
        _("Data Prevista de Entrega"), null=True, blank=True,
    )
    data_entrega_efetiva = models.DateField(
        _("Data Efetiva de Entrega"), null=True, blank=True,
    )

    # ── Valores ──────────────────────────────────────────────────────────────
    valor_total = models.DecimalField(
        _("Valor Total (R$)"),
        max_digits=14, decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
        help_text=_("Calculado automaticamente a partir dos itens."),
    )

    # ── Nota Fiscal ──────────────────────────────────────────────────────────
    numero_nota_fiscal = models.CharField(
        _("Nº da Nota Fiscal"),
        max_length=50, blank=True, default="",
    )
    data_nota_fiscal = models.DateField(
        _("Data da Nota Fiscal"), null=True, blank=True,
    )
    tipo_nota_fiscal = models.CharField(
        _("Tipo de NF"),
        max_length=20,
        choices=TipoNotaFiscal.choices,
        blank=True, default="",
    )

    # ── Controle ─────────────────────────────────────────────────────────────
    observacoes = models.TextField(
        _("Observações"), blank=True, default="",
    )
    motivo_cancelamento = models.TextField(
        _("Motivo do Cancelamento"), blank=True, default="",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos_compra_criados",
        verbose_name=_("Criado por"),
    )
    recebido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="pedidos_compra_recebidos_por",
        verbose_name=_("Recebido por"),
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Pedido de Compra")
        verbose_name_plural = _("Pedidos de Compra")
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["solicitacao", "fornecedor"]),
            models.Index(fields=["status"]),
            models.Index(fields=["numero_pedido"]),
        ]
        permissions = [
            ("pode_emitir_pedido_compra", "Pode emitir Pedido de Compra"),
            ("pode_receber_pedido_compra", "Pode dar entrada em Pedido de Compra"),
            ("pode_cancelar_pedido_compra", "Pode cancelar Pedido de Compra"),
            ("pode_visualizar_pedido_compra", "Pode visualizar Pedido de Compra"),
        ]

    def __str__(self):
        return f"PC {self.numero} — {self.fornecedor.nome_fantasia}"

    def get_absolute_url(self):
        return reverse("suprimentos:pc_detalhe", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        # Geração de número interno automático
        if not self.numero:
            hoje = timezone.now()
            prefix = f"PC-{hoje.strftime('%Y%m')}"
            ultimo = (
                PedidoCompra.objects.filter(numero__startswith=prefix)
                .order_by("-numero")
                .first()
            )
            seq = int(ultimo.numero.split("-")[-1]) + 1 if ultimo else 1
            self.numero = f"{prefix}-{seq:04d}"
        super().save(*args, **kwargs)

    def recalcular_total(self):
        """Recalcula valor_total a partir dos itens. Salva no banco."""
        from django.db.models import Sum
        total = (
            self.itens.aggregate(t=Sum("valor_total"))["t"]
            or Decimal("0.00")
        )
        self.valor_total = total
        self.save(update_fields=["valor_total", "atualizado_em"])
        return total
    
    def atualizar_status_entrega(self):
        """Atualiza o status com base no total recebido vs. pedido."""
        # 🔑 ItemPedidoCompra direto, ignorando qualquer cache de prefetch
        agg = ItemPedidoCompra.objects.filter(pedido_compra=self).aggregate(
            total_pedido=Sum("quantidade"),
            total_receb=Sum("quantidade_recebida"),
        )
        total_pedido = agg["total_pedido"] or Decimal("0")
        total_receb = agg["total_receb"] or Decimal("0")

        if total_pedido <= 0:
            return

        if total_receb <= 0:
            self.status = self.StatusPC.ENVIADO_FORNECEDOR
        elif total_receb < total_pedido:
            self.status = self.StatusPC.ENTREGA_PARCIAL
        else:
            self.status = self.StatusPC.ENTREGUE
            if not self.data_entrega_efetiva:
                self.data_entrega_efetiva = timezone.now().date()

        self.save(update_fields=["status", "data_entrega_efetiva", "atualizado_em"])

    # ✅ AGORA com 4 espaços — métodos REAIS da classe
    @property
    def total_itens(self) -> int:
        return self.itens.count()

    @property
    def pode_cancelar(self) -> bool:
        return self.status not in (self.StatusPC.RECEBIDO, self.StatusPC.CANCELADO)

    @property
    def esta_atrasado(self) -> bool:
        """True se a data prevista já passou e ainda não foi entregue."""
        if not self.data_entrega_prevista:
            return False
        if self.status in (
            self.StatusPC.ENTREGUE,
            self.StatusPC.RECEBIDO,
            self.StatusPC.CANCELADO,
        ):
            return False
        return timezone.now().date() > self.data_entrega_prevista


# ═════════════════════════════════════════════════════════════════════════════
# 11. ITEM DO PEDIDO DE COMPRA (NOVO — Fase 1)
# ═════════════════════════════════════════════════════════════════════════════

class ItemPedidoCompra(TimestampedModel):
    """
    Linha do Pedido de Compra. Vincula-se à Cotação escolhida e ao ItemSolicitacao.
    Os valores são SNAPSHOT da cotação no momento da emissão do PC
    (não muda mesmo se a cotação original for editada depois).
    """
    pedido_compra = models.ForeignKey(
        PedidoCompra,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name=_("Pedido de Compra"),
    )
    cotacao = models.ForeignKey(
        Cotacao,
        on_delete=models.PROTECT,
        related_name="itens_pedido_compra_gerados",
        verbose_name=_("Cotação Origem"),
        help_text=_("Cotação aprovada que originou este item."),
    )
    item_solicitacao = models.ForeignKey(
        ItemSolicitacao,
        on_delete=models.PROTECT,
        related_name="itens_pedido_compra",
        verbose_name=_("Item da Solicitação"),
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="itens_pedido_compra",
        verbose_name=_("Material"),
    )
    quantidade = models.DecimalField(
        _("Quantidade"),
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    valor_unitario = models.DecimalField(
        _("Valor Unitário (R$)"),
        max_digits=12, decimal_places=2,
        help_text=_("Snapshot da cotação no momento da emissão."),
    )
    valor_total = models.DecimalField(
        _("Valor Total (R$)"),
        max_digits=14, decimal_places=2,
        editable=False,
        default=Decimal("0.00"),
    )
    quantidade_recebida = models.DecimalField(
        _("Quantidade Recebida"),
        max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Atualizada no recebimento do PC."),
    )
    observacao = models.CharField(
        _("Observação"),
        max_length=255, blank=True, default="",
    )

    class Meta:
        verbose_name = _("Item do Pedido de Compra")
        verbose_name_plural = _("Itens do Pedido de Compra")
        ordering = ["material__classificacao", "material__descricao"]
        indexes = [
            models.Index(fields=["pedido_compra"]),
            models.Index(fields=["cotacao"]),
        ]

    def __str__(self):
        return f"{self.quantidade}x {self.material.descricao}"

    def save(self, *args, **kwargs):
        # Calcula valor_total automaticamente
        self.valor_total = (self.quantidade * self.valor_unitario).quantize(
            Decimal("0.01")
        )
        super().save(*args, **kwargs)
        # Recalcula total do PC pai
        self.pedido_compra.recalcular_total()

    def delete(self, *args, **kwargs):
        pc = self.pedido_compra
        super().delete(*args, **kwargs)
        pc.recalcular_total()

    @property
    def saldo_receber(self) -> Decimal:
        """Quantidade ainda não recebida."""
        return self.quantidade - self.quantidade_recebida

    @property
    def recebimento_completo(self) -> bool:
        return self.quantidade_recebida >= self.quantidade
    
    
    @property
    def qtd_entregue(self):
        """Quantidade já recebida deste item."""
        return self.quantidade_recebida or Decimal("0")

    @property
    def saldo(self):
        """Quantidade ainda pendente de recebimento."""
        return (self.quantidade or Decimal("0")) - (self.quantidade_recebida or Decimal("0"))

    @property
    def progresso_pct(self):
        if not self.quantidade:
            return Decimal("0")
        recebida = self.quantidade_recebida or Decimal("0")
        return (recebida / self.quantidade * 100).quantize(Decimal("0.1"))

    
    