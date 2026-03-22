
#    ┌─────────────────────────────────────────────────────────────────┐
#    │#  1. VÍNCULO: Material (suprimentos) ←→ Equipamento (SST)       │
#    │# 2. SIGNAL: Pedido RECEBIDO → entrada automática no estoque     │
#    │#  3. ESTOQUE CONSUMO: Novo modelo leve para consumíveis         │
#    └─────────────────────────────────────────────────────────────────┘

#FLUXO APÓS A SOLUÇÃO:
                                                                    
#Pedido RECEBIDO ──signal──┬─► EPI → MovimentacaoEstoque (SST) ✅
#                          ├─► CONSUMO → EstoqueConsumo (novo) ✅    
#                          └─► FERRAMENTA → Ferramenta.quantidade ✅ 

# suprimentos/models.py

import uuid
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

from usuario.models import Filial
from core.managers import FilialManager
from logradouro.models import Logradouro


# ═════════════════════════════════════════════════
# PARCEIRO (já existente — preservado)
# ═════════════════════════════════════════════════
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
        related_name='parceiros', verbose_name=_("Endereço"),
        null=True, blank=True,
    )
    observacoes = models.TextField(blank=True, verbose_name=_("Observações"))

    eh_fabricante = models.BooleanField(default=False, verbose_name=_("É Fabricante?"))
    eh_fornecedor = models.BooleanField(default=False, verbose_name=_("É Fornecedor?"))

    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='parceiros', verbose_name=_("Filial"),
        null=True, blank=True,
    )
    objects = FilialManager()

    class Meta:
        verbose_name = _("Parceiro")
        verbose_name_plural = _("Parceiros")
        ordering = ['nome_fantasia']

    def __str__(self):
        return self.nome_fantasia or self.razao_social

    def get_absolute_url(self):
        return reverse('suprimentos:parceiro_detail', kwargs={'pk': self.pk})


# ═════════════════════════════════════════════════
# CHOICES REUTILIZÁVEIS
# ═════════════════════════════════════════════════
class CategoriaMaterial(models.TextChoices):
    CONSUMO = 'CONSUMO', 'Consumo'
    EPI = 'EPI', 'EPI'
    FERRAMENTA = 'FERRAMENTA', 'Ferramenta'


class TipoMaterial(models.TextChoices):
    CIVIL = 'CIVIL', 'Civil'
    ELETRICA = 'ELETRICA', 'Elétrica'
    HIDRAULICA = 'HIDRAULICA', 'Hidráulica'
    LIMPEZA = 'LIMPEZA', 'Limpeza'
    ESCRITORIO = 'ESCRITORIO', 'Escritório'
    CREME = 'CREME', 'Creme'
    EPI = 'EPI', 'EPI'
    PRODUTO_QUIMICO = 'PRODUTO_QUIMICO', 'Produto Químico'
    AR_CONDICIONADO = 'AR_CONDICIONADO', 'Ar Condicionado'
    PISCINA = 'PISCINA', 'Piscina'


class UnidadeMedida(models.TextChoices):
    PC = 'PC', 'Peça'
    PAR = 'PAR', 'Par'
    LATA = 'LATA', 'Lata'
    ROLO = 'ROLO', 'Rolo'
    GALAO = 'GALAO', 'Galão'
    PACOTE = 'PACOTE', 'Pacote'
    JOGO = 'JOGO', 'Jogo'
    KIT = 'KIT', 'Kit'
    CAIXA = 'CAIXA', 'Caixa'
    FRASCO = 'FRASCO', 'Frasco'
    POTE = 'POTE', 'Pote'
    KG = 'KG', 'Kg'
    LITRO = 'LITRO', 'Litro'
    CARTELA = 'CARTELA', 'Cartela'
    UNID = 'UNID', 'Unidade'


# ═════════════════════════════════════════════════
# 1. CATÁLOGO DE MATERIAIS
# ═════════════════════════════════════════════════
class Material(models.Model):
    """Catálogo centralizado de materiais (EPI, Consumo, Ferramenta)."""

    codigo = models.CharField(
        "Código", max_length=20, unique=True, blank=True,
        help_text="Gerado automaticamente se deixado em branco.",
    )
    descricao = models.CharField("Descrição", max_length=500)
    classificacao = models.CharField(
        "Classificação", max_length=20,
        choices=CategoriaMaterial.choices,
    )
    tipo = models.CharField(
        "Tipo", max_length=30,
        choices=TipoMaterial.choices,
    )
    marca = models.CharField("Marca", max_length=100, blank=True, default='')
    unidade = models.CharField(
        "Unidade", max_length=20,
        choices=UnidadeMedida.choices,
        default=UnidadeMedida.PC,
    )
    valor_unitario = models.DecimalField(
        "Valor Unitário (R$)", max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    # ═══ NOVO: Vínculo com estoque dos outros módulos ═══
    equipamento_epi = models.ForeignKey(
        'seguranca_trabalho.Equipamento',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='materiais_vinculados',
        verbose_name="Equipamento EPI vinculado",
        help_text="Para materiais EPI: vincule ao equipamento de SST para entrada automática no estoque.",
    )
    ferramenta_ref = models.ForeignKey(
        'ferramentas.Ferramenta',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='materiais_vinculados',
        verbose_name="Ferramenta vinculada",
        help_text="Para ferramentas: vincule para atualizar quantidade ao receber pedido.",
    )

    # ═══ NOVO: Vínculo com Tributação ═══
    ncm = models.ForeignKey(
        'tributacao.NCM',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='materiais',
        verbose_name="NCM",
        help_text="Classificação fiscal do material (Nomenclatura Comum do Mercosul)",
    )
    grupo_tributario = models.ForeignKey(
        'tributacao.GrupoTributario',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='materiais',
        verbose_name="Grupo Tributário",
        help_text="Perfil fiscal para cálculo automático de impostos na compra",
    )

    def calcular_custo_compra(self, valor_total, quantidade=1):
        """
        Calcula custo real de aquisição usando o grupo tributário.
        Se não houver grupo, retorna valor bruto.
        """
        from decimal import Decimal
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

    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiais"
        ordering = ['classificacao', 'tipo', 'descricao']
        indexes = [
            models.Index(fields=['classificacao', 'tipo']),
            models.Index(fields=['descricao']),
        ]

    def __str__(self):
        marca = f" ({self.marca})" if self.marca else ""
        return f"{self.descricao}{marca}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            prefix = self.classificacao[:3].upper()
            self.codigo = f"{prefix}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    @property
    def tem_vinculo_estoque(self):
        """Verifica se o material está vinculado a um item de estoque."""
        if self.classificacao == CategoriaMaterial.EPI:
            return self.equipamento_epi is not None
        elif self.classificacao == CategoriaMaterial.FERRAMENTA:
            return self.ferramenta_ref is not None
        # CONSUMO sempre tem estoque próprio (EstoqueConsumo)
        return True


# ═════════════════════════════════════════════════
# 2. CONTRATO / CM (vinculado a Filial)
# ═════════════════════════════════════════════════
class Contrato(models.Model):
    """
    Contrato (CM) vinculado obrigatoriamente a uma Filial.
    Cada contrato tem verbas mensais (VerbaContrato).
    """

    cm = models.CharField("CM (Código)", max_length=20, unique=True)
    cliente = models.CharField("Cliente", max_length=255)
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='contratos', verbose_name="Filial",
    )
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = FilialManager()

    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ['cm']

    def __str__(self):
        return f"CM {self.cm} - {self.cliente}"

    def get_absolute_url(self):
        return reverse('suprimentos:contrato_detalhe', kwargs={'pk': self.pk})

    def verba_do_mes(self, ano=None, mes=None):
        """Retorna a VerbaContrato do mês atual (cria se não existir)."""
        hoje = timezone.now().date()
        ano = ano or hoje.year
        mes = mes or hoje.month
        verba, _ = VerbaContrato.objects.get_or_create(
            contrato=self, ano=ano, mes=mes,
            defaults={
                'verba_epi': Decimal('0.00'),
                'verba_consumo': Decimal('0.00'),
                'verba_ferramenta': Decimal('0.00'),
            }
        )
        return verba


# ═════════════════════════════════════════════════
# 3. VERBA MENSAL DO CONTRATO
# ═════════════════════════════════════════════════
class VerbaContrato(models.Model):
    """
    Verbas mensais de um contrato. Permite histórico mês a mês
    e comparação Verba × Compra (indicadores).
    """

    contrato = models.ForeignKey(
        Contrato, on_delete=models.CASCADE,
        related_name='verbas', verbose_name="Contrato",
    )
    ano = models.PositiveSmallIntegerField("Ano")
    mes = models.PositiveSmallIntegerField("Mês")

    verba_epi = models.DecimalField(
        "Verba EPI (R$)", max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
    )
    verba_consumo = models.DecimalField(
        "Verba Consumo (R$)", max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
    )
    verba_ferramenta = models.DecimalField(
        "Verba Ferramenta (R$)", max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
    )

    class Meta:
        verbose_name = "Verba Mensal"
        verbose_name_plural = "Verbas Mensais"
        unique_together = ['contrato', 'ano', 'mes']
        ordering = ['-ano', '-mes']

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
        ).aggregate(t=Sum('valor_total'))['t']
        return total or Decimal('0.00')

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


# ═════════════════════════════════════════════════
# 4. PEDIDO DE MATERIAL
# ═════════════════════════════════════════════════
class Pedido(models.Model):
    """
    Pedido de materiais vinculado a um contrato.
    Workflow: Rascunho → Pendente → Aprovado/Reprovado → Entregue → Recebido
    Aprovação exclusiva do grupo Gerente.
    """

    class StatusChoices(models.TextChoices):
        RASCUNHO = 'RASCUNHO', 'Rascunho'
        PENDENTE = 'PENDENTE', 'Pendente de Aprovação'
        APROVADO = 'APROVADO', 'Aprovado'
        REPROVADO = 'REPROVADO', 'Reprovado'
        ENTREGUE = 'ENTREGUE', 'Entregue'
        RECEBIDO = 'RECEBIDO', 'Recebido'
        CANCELADO = 'CANCELADO', 'Cancelado'

    numero = models.CharField(
        "Nº Pedido", max_length=30, unique=True, editable=False,
    )
    contrato = models.ForeignKey(
        Contrato, on_delete=models.PROTECT,
        related_name='pedidos', verbose_name="Contrato",
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='pedidos_solicitados', verbose_name="Solicitante",
    )
    aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='pedidos_aprovados', verbose_name="Aprovador",
        null=True, blank=True,
    )
    recebedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='pedidos_recebidos', verbose_name="Recebido por",
        null=True, blank=True,
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        verbose_name="Filial", null=True, blank=True,
    )
    status = models.CharField(
        "Status", max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.RASCUNHO,
    )
    data_pedido = models.DateTimeField("Data do Pedido", auto_now_add=True)
    data_aprovacao = models.DateTimeField("Data Aprovação", null=True, blank=True)
    data_entrega = models.DateField("Data Entrega", null=True, blank=True)
    data_recebimento = models.DateTimeField("Data Recebimento", null=True, blank=True)
    observacao = models.TextField("Observação", blank=True, default='')
    motivo_reprovacao = models.TextField("Motivo Reprovação", blank=True, default='')

    # ═══ NOVO: flag para evitar dupla entrada no estoque ═══
    estoque_processado = models.BooleanField(
        "Estoque Processado",
        default=False,
        editable=False,
        help_text="Indica se a entrada no estoque já foi gerada para este pedido.",
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Pedido de Material"
        verbose_name_plural = "Pedidos de Material"
        ordering = ['-data_pedido']
        permissions = [
            ("pode_aprovar_pedido", "Pode aprovar pedidos de material"),
        ]

    def __str__(self):
        return f"Pedido {self.numero} — {self.contrato.cliente}"

    def get_absolute_url(self):
        return reverse('suprimentos:pedido_detalhe', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.numero:
            hoje = timezone.now()
            prefix = f"PED-{hoje.strftime('%Y%m')}"
            ultimo = Pedido.objects.filter(
                numero__startswith=prefix
            ).order_by('-numero').first()
            seq = int(ultimo.numero.split('-')[-1]) + 1 if ultimo else 1
            self.numero = f"{prefix}-{seq:04d}"
        super().save(*args, **kwargs)

    @property
    def valor_total(self):
        from django.db.models import Sum
        return self.itens.aggregate(t=Sum('valor_total'))['t'] or Decimal('0.00')

    def totais_por_classificacao(self):
        """Retorna dict {CONSUMO: x, EPI: y, FERRAMENTA: z}."""
        from django.db.models import Sum
        qs = self.itens.values(
            'material__classificacao'
        ).annotate(total=Sum('valor_total'))
        return {
            item['material__classificacao']: item['total']
            for item in qs
        }

    def verificar_verba(self):
        """Verifica se o pedido cabe na verba mensal do contrato."""
        verba = self.contrato.verba_do_mes(
            self.data_pedido.year, self.data_pedido.month
        )
        totais = self.totais_por_classificacao()
        erros = []

        checks = [
            ('EPI', verba.saldo_epi),
            ('CONSUMO', verba.saldo_consumo),
            ('FERRAMENTA', verba.saldo_ferramenta),
        ]
        for cat, saldo in checks:
            pedido_val = totais.get(cat, Decimal('0.00'))
            if pedido_val > saldo:
                erros.append(
                    f"{cat}: pedido R$ {pedido_val:.2f} > saldo R$ {saldo:.2f}"
                )

        return len(erros) == 0, erros
    @property
    def resumo_tributario(self):
        """Retorna resumo consolidado de impostos de todos os itens."""
        from django.db.models import Sum

        totais = self.itens.aggregate(
            valor_produtos=Sum('valor_total'),
            sum_custo_real=Sum('custo_real'),
            sum_creditos=Sum('total_creditos'),
            sum_impostos=Sum('total_impostos'),
        )

        valor_produtos = totais['valor_produtos'] or Decimal('0.00')
        custo_real = totais['sum_custo_real'] or Decimal('0.00')
        total_creditos = totais['sum_creditos'] or Decimal('0.00')
        total_impostos = totais['sum_impostos'] or Decimal('0.00')
        total_nfe = valor_produtos + (total_impostos - total_creditos)  # aproximação

        pct = Decimal('0.00')
        if valor_produtos > 0:
            pct = ((total_creditos / valor_produtos) * 100).quantize(Decimal('0.01'))

        # Quantos itens têm grupo tributário
        total_itens = self.itens.count()
        itens_com_grupo = self.itens.filter(
            material__grupo_tributario__isnull=False
        ).count()

        return {
            'valor_produtos': valor_produtos,
            'total_impostos': total_impostos,
            'total_creditos': total_creditos,
            'total_nfe': total_nfe,
            'custo_real': custo_real,
            'percentual_economia': pct,
            'itens_com_grupo': itens_com_grupo,
            'total_itens': total_itens,
            'cobertura_tributaria': (
                f"{itens_com_grupo}/{total_itens}"
            ),
        }


# ═════════════════════════════════════════════════
# 5. ITEM DO PEDIDO
# ═════════════════════════════════════════════════
class ItemPedido(models.Model):
    """Linha do pedido: material + quantidade + valor."""

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name='itens', verbose_name="Pedido",
    )
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name='itens_pedido', verbose_name="Material",
    )
    quantidade = models.PositiveIntegerField(
        "Quantidade", validators=[MinValueValidator(1)],
    )
    valor_unitario = models.DecimalField(
        "Valor Unitário (R$)", max_digits=10, decimal_places=2,
    )
    valor_total = models.DecimalField(
        "Valor Total (R$)", max_digits=12, decimal_places=2,
        editable=False, default=Decimal('0.00'),
    )
    observacao = models.CharField(
        "Observação", max_length=255, blank=True, default='',
    )

    # ═══ NOVO: Campos calculados de tributação ═══
    custo_real = models.DecimalField(
        "Custo Real (R$)", max_digits=14, decimal_places=2,
        default=Decimal('0.00'), editable=False,
        help_text="Valor total menos créditos fiscais recuperáveis",
    )
    total_creditos = models.DecimalField(
        "Créditos Fiscais (R$)", max_digits=14, decimal_places=2,
        default=Decimal('0.00'), editable=False,
    )
    total_impostos = models.DecimalField(
        "Total Impostos (R$)", max_digits=14, decimal_places=2,
        default=Decimal('0.00'), editable=False,
    )

    def calcular_impostos(self):
        """Calcula impostos usando o grupo tributário do material."""
        valor = self.quantidade * self.valor_unitario
        return self.material.calcular_custo_compra(valor, self.quantidade)

    # ATUALIZAR o save() existente:
    def save(self, *args, **kwargs):
        self.valor_total = self.quantidade * self.valor_unitario
        # ═══ NOVO: Calcular tributação ao salvar ═══
        calc = self.calcular_impostos()
        self.custo_real = calc.get("custo_real", self.valor_total)
        self.total_creditos = calc.get("total_creditos", Decimal("0.00"))
        self.total_impostos = calc.get("total_impostos", Decimal("0.00"))
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Item do Pedido"
        verbose_name_plural = "Itens do Pedido"
        ordering = ['material__classificacao', 'material__tipo']

    def __str__(self):
        return f"{self.quantidade}x {self.material.descricao}"

    def save(self, *args, **kwargs):
        self.valor_total = self.quantidade * self.valor_unitario
        super().save(*args, **kwargs)


# ═════════════════════════════════════════════════
# 6. ESTOQUE DE CONSUMO
# ═════════════════════════════════════════════════
class EstoqueConsumo(models.Model):
    """
    Controle de estoque para materiais de CONSUMO por contrato/filial.
    EPIs usam o estoque de SST (MovimentacaoEstoque).
    Ferramentas usam o módulo ferramentas (Ferramenta.quantidade).
    """

    class TipoMovimento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SAIDA = 'SAIDA', 'Saída'
        AJUSTE = 'AJUSTE', 'Ajuste'

    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name='movimentacoes_consumo',
        verbose_name="Material",
    )
    contrato = models.ForeignKey(
        Contrato, on_delete=models.PROTECT,
        related_name='estoque_consumo',
        verbose_name="Contrato",
    )
    tipo = models.CharField(
        "Tipo", max_length=10,
        choices=TipoMovimento.choices,
    )
    quantidade = models.IntegerField("Quantidade")
    pedido = models.ForeignKey(
        Pedido, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='movimentacoes_estoque',
        verbose_name="Pedido Origem",
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        verbose_name="Responsável",
    )
    justificativa = models.CharField(
        "Justificativa", max_length=255, blank=True, default='',
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        verbose_name="Filial",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = FilialManager()

    class Meta:
        verbose_name = "Movimentação de Estoque (Consumo)"
        verbose_name_plural = "Movimentações de Estoque (Consumo)"
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.material.descricao} ({self.quantidade})"

    @classmethod
    def saldo_material(cls, material_id, contrato_id, filial_id):
        """Calcula saldo atual de um material de consumo."""
        from django.db.models import Sum, Q
        resultado = cls.objects.filter(
            material_id=material_id,
            contrato_id=contrato_id,
            filial_id=filial_id,
        ).aggregate(
            entradas=Sum('quantidade', filter=Q(tipo='ENTRADA'), default=0),
            saidas=Sum('quantidade', filter=Q(tipo='SAIDA'), default=0),
        )
        return resultado['entradas'] - resultado['saidas']

    @classmethod
    def saldo_por_contrato(cls, contrato_id, filial_id):
        """Retorna saldo de todos os materiais de consumo de um contrato."""
        from django.db.models import Sum, Q
        return cls.objects.filter(
            contrato_id=contrato_id,
            filial_id=filial_id,
        ).values(
            'material__id', 'material__descricao', 'material__unidade',
        ).annotate(
            entradas=Sum('quantidade', filter=Q(tipo='ENTRADA'), default=0),
            saidas=Sum('quantidade', filter=Q(tipo='SAIDA'), default=0),
        ).order_by('material__descricao')

