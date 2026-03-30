
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

    @property
    def info_tributaria_unitaria(self):
        """Calcula impostos para 1 unidade do material (para exibição no catálogo)."""
        if not self.grupo_tributario:
            return {'sem_grupo': True}

        try:
            calc = self.calcular_custo_compra(self.valor_unitario, 1)
            calc['sem_grupo'] = False

            # Percentual de economia
            pct = Decimal('0.00')
            if self.valor_unitario > 0:
                creditos = calc.get('total_creditos', Decimal('0.00'))
                pct = ((creditos / self.valor_unitario) * 100).quantize(Decimal('0.01'))
            calc['percentual_economia'] = pct

            return calc
        except Exception:
            return {'sem_grupo': True}


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
# CHOICES ADICIONAIS
# ═════════════════════════════════════════════════

class TipoObra(models.TextChoices):
    CM = 'CM', 'CM - Contrato de Manutenção'
    CR = 'CR', 'CR - Contrato de Reforma'
    VE = 'VE', 'VE - Venda'


class TipoNotaFiscal(models.TextChoices):
    MATERIAL = 'MATERIAL', 'Material'
    SERVICO = 'SERVICO', 'Serviço'
    MATERIAL_SERVICO = 'MATERIAL_SERVICO', 'Material/Serviço'


# ═════════════════════════════════════════════════
# 4. PEDIDO DE MATERIAL (REFATORADO)
# ═════════════════════════════════════════════════

def pedido_upload_path(instance, filename):
    return f"suprimentos/pedidos/{instance.pedido.numero}/{filename}"


class Pedido(models.Model):
    """
    Pedido de material — Solicitante cria, Gerente aprova/reprova/devolve.
    Quando APROVADO, gera automaticamente uma SolicitacaoCompra.
    Workflow: Rascunho → Pendente ⇄ Revisão → Aprovado → (gera Solicitação)
              ou → Reprovado / Cancelado
    """

    class StatusChoices(models.TextChoices):
        RASCUNHO = 'RASCUNHO', 'Rascunho'
        PENDENTE = 'PENDENTE', 'Pendente de Aprovação'
        REVISAO = 'REVISAO', 'Em Revisão pelo Solicitante'
        APROVADO = 'APROVADO', 'Aprovado'
        REPROVADO = 'REPROVADO', 'Reprovado'
        ENTREGUE = 'ENTREGUE', 'Entregue'
        RECEBIDO = 'RECEBIDO', 'Recebido'
        CANCELADO = 'CANCELADO', 'Cancelado'

    # ───── Identificação ─────
    numero = models.CharField(
        "Nº Pedido", max_length=30, unique=True, editable=False,
    )
    contrato = models.ForeignKey(
        Contrato, on_delete=models.PROTECT,
        related_name='pedidos', verbose_name="Contrato",
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

    # ───── NOVO: Tipo de Obra ─────
    tipo_obra = models.CharField(
        "Tipo de Obra", max_length=2,
        choices=TipoObra.choices,
        default=TipoObra.CM,
    )

    # ───── NOVO: Descrição detalhada (1 material por solicitação) ─────
    descricao_material = models.TextField(
        "Descrição do Material",
        blank=True, default='',
        help_text=(
            "Informe uma descrição DETALHADA e PRECISA do material. "
            "Isso garante maior agilidade, assertividade e redução de "
            "retrabalhos no processo de cotação e compra."
        ),
    )
    quantidade = models.DecimalField(
        "Quantidade", max_digits=12, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    unidade_medida = models.CharField(
        "Unidade de Medida", max_length=20,
        choices=UnidadeMedida.choices,
        default=UnidadeMedida.UNID,
    )
    tipo_insumo = models.CharField(
        "Tipo de Insumo", max_length=30,
        choices=TipoMaterial.choices,
        blank=True, default='',
    )
    data_necessaria = models.DateField(
        "Data Necessária para Entrega",
        null=True, blank=True,
        help_text="Data em que o material deve estar disponível no contrato.",
    )

    # ───── Responsáveis (todos são funcionários/usuarios) ─────
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='pedidos_solicitados', verbose_name="Solicitante",
    )
    aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='pedidos_aprovados', verbose_name="Aprovador",
        null=True, blank=True,
        help_text="Gerente responsável pela aprovação.",
    )
    recebedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='pedidos_recebidos', verbose_name="Recebido por",
        null=True, blank=True,
    )

    # ───── Datas do Workflow ─────
    data_pedido = models.DateTimeField("Data do Pedido", auto_now_add=True)
    data_aprovacao = models.DateTimeField("Data Aprovação", null=True, blank=True)
    data_entrega = models.DateField("Data Entrega", null=True, blank=True)
    data_recebimento = models.DateTimeField("Data Recebimento", null=True, blank=True)

    # ───── Revisão (loop Gerente ↔ Solicitante) ─────
    motivo_revisao = models.TextField(
        "Motivo da Revisão/Devolução", blank=True, default='',
        help_text="Preenchido pelo Gerente ao devolver para revisão.",
    )
    motivo_reprovacao = models.TextField(
        "Motivo Reprovação", blank=True, default='',
    )

    # ───── Observações e Controle ─────
    observacao = models.TextField("Observação", blank=True, default='')

    # ═══ Flag estoque (mantido) ═══
    estoque_processado = models.BooleanField(
        "Estoque Processado", default=False, editable=False,
        help_text="Indica se a entrada no estoque já foi gerada.",
    )

    # ═══ NOVO: Vínculo com SolicitacaoCompra ═══
    solicitacao_gerada = models.OneToOneField(
        'SolicitacaoCompra', on_delete=models.SET_NULL,
        null=True, blank=True, editable=False,
        related_name='pedido_origem',
        verbose_name="Solicitação de Compra Gerada",
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
        from django.db.models import Sum
        qs = self.itens.values(
            'material__classificacao'
        ).annotate(total=Sum('valor_total'))
        return {
            item['material__classificacao']: item['total']
            for item in qs
        }

    def verificar_verba(self):
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

    def gerar_solicitacao_compra(self):
        """
        Gera uma SolicitacaoCompra a partir deste pedido aprovado.
        Chamado automaticamente ao aprovar.
        """
        if self.solicitacao_gerada:
            return self.solicitacao_gerada

        sol = SolicitacaoCompra(
            filial=self.filial,
            status=SolicitacaoCompra.StatusChoices.FAZER_COTACAO,
            tipo_obra=self.tipo_obra,
            contrato=self.contrato,
            solicitante=self.solicitante,
            aprovador_inicial=self.aprovador,
            descricao_material=self.descricao_material,
            quantidade=self.quantidade,
            unidade_medida=self.unidade_medida,
            tipo_insumo=self.tipo_insumo,
            data_necessaria=self.data_necessaria,
            data_aprovacao_inicial=self.data_aprovacao,
        )
        sol.save()

        # Copiar anexos do pedido para a solicitação
        for anexo_pedido in self.anexos.all():
            AnexoSolicitacao.objects.create(
                solicitacao=sol,
                arquivo=anexo_pedido.arquivo,
                descricao=anexo_pedido.descricao,
                enviado_por=anexo_pedido.enviado_por,
            )

        # Copiar itens como referência na observação
        itens_txt = []
        for item in self.itens.select_related('material').all():
            itens_txt.append(
                f"- {item.quantidade}x {item.material.descricao} "
                f"(R$ {item.valor_unitario} un. = R$ {item.valor_total})"
            )
        if itens_txt:
            sol.observacoes = (
                f"Itens do Pedido {self.numero}:\n" + "\n".join(itens_txt)
            )
            sol.save(update_fields=['observacoes'])

        # Registrar histórico
        HistoricoSolicitacao.registrar(
            solicitacao=sol,
            descricao=(
                f"Solicitação gerada automaticamente a partir do "
                f"Pedido {self.numero} aprovado por "
                f"{self.aprovador.get_full_name() if self.aprovador else 'N/A'}."
            ),
            responsavel=self.aprovador,
            status_novo='FAZER_COTACAO',
        )

        self.solicitacao_gerada = sol
        self.save(update_fields=['solicitacao_gerada'])

        return sol

    @property
    def resumo_tributario(self):
        valor_produtos = Decimal('0.00')
        total_impostos = Decimal('0.00')
        total_creditos = Decimal('0.00')
        custo_real = Decimal('0.00')
        total_nfe = Decimal('0.00')
        itens_com_grupo = 0
        total_itens = 0

        for item in self.itens.select_related('material__grupo_tributario').all():
            total_itens += 1
            valor_item = item.quantidade * item.valor_unitario
            valor_produtos += valor_item

            if item.material.grupo_tributario:
                itens_com_grupo += 1
                try:
                    calc = item.calcular_impostos()
                    total_impostos += calc.get('total_impostos', Decimal('0.00'))
                    total_creditos += calc.get('total_creditos', Decimal('0.00'))
                    custo_real += calc.get('custo_real', Decimal('0.00'))
                    total_nfe += calc.get('total_nfe', Decimal('0.00'))
                except Exception:
                    custo_real += valor_item
                    total_nfe += valor_item
            else:
                custo_real += valor_item
                total_nfe += valor_item

        pct = Decimal('0.00')
        if valor_produtos > 0:
            pct = ((total_creditos / valor_produtos) * 100).quantize(Decimal('0.01'))

        return {
            'valor_produtos': valor_produtos,
            'total_impostos': total_impostos,
            'total_creditos': total_creditos,
            'total_nfe': total_nfe,
            'custo_real': custo_real,
            'percentual_economia': pct,
            'itens_com_grupo': itens_com_grupo,
            'total_itens': total_itens,
            'cobertura_tributaria': f"{itens_com_grupo}/{total_itens}",
        }


# ═════════════════════════════════════════════════
# 4b. ANEXOS DO PEDIDO (NOVO)
# ═════════════════════════════════════════════════

def anexo_pedido_upload_path(instance, filename):
    return f"suprimentos/pedidos/{instance.pedido.numero}/{filename}"


class AnexoPedido(models.Model):
    """Arquivo anexo ao pedido (PDF, foto, catálogo, etc.)."""

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name='anexos', verbose_name="Pedido",
    )
    arquivo = models.FileField(
        "Arquivo", upload_to=anexo_pedido_upload_path,
    )
    descricao = models.CharField(
        "Descrição", max_length=255, blank=True, default='',
    )
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="Enviado por",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Anexo do Pedido"
        verbose_name_plural = "Anexos do Pedido"
        ordering = ['-criado_em']

    def __str__(self):
        return f"Anexo: {self.descricao or self.arquivo.name}"

    @property
    def nome_arquivo(self):
        return self.arquivo.name.split('/')[-1] if self.arquivo else ''

    @property
    def extensao(self):
        nome = self.nome_arquivo
        return nome.rsplit('.', 1)[-1].lower() if '.' in nome else ''

    @property
    def is_imagem(self):
        return self.extensao in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp')

    @property
    def is_pdf(self):
        return self.extensao == 'pdf'


# ═════════════════════════════════════════════════
# 4c. HISTÓRICO DO PEDIDO (NOVO)
# ═════════════════════════════════════════════════

class HistoricoPedido(models.Model):
    """Registro de cada alteração no pedido (versionamento)."""

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name='historico', verbose_name="Pedido",
    )
    versao = models.PositiveIntegerField("Versão")
    descricao = models.TextField("Descrição das Alterações")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="Responsável",
    )
    status_anterior = models.CharField(
        "Status Anterior", max_length=25, blank=True, default='',
    )
    status_novo = models.CharField(
        "Status Novo", max_length=25, blank=True, default='',
    )
    criado_em = models.DateTimeField("Data", auto_now_add=True)

    class Meta:
        verbose_name = "Histórico do Pedido"
        verbose_name_plural = "Histórico dos Pedidos"
        ordering = ['-versao']

    def __str__(self):
        return f"v{self.versao} — {self.descricao[:60]}"

    @classmethod
    def registrar(cls, pedido, descricao, responsavel,
                  status_anterior='', status_novo=''):
        ultima_versao = cls.objects.filter(
            pedido=pedido
        ).order_by('-versao').values_list('versao', flat=True).first() or 0

        return cls.objects.create(
            pedido=pedido,
            versao=ultima_versao + 1,
            descricao=descricao,
            responsavel=responsavel,
            status_anterior=status_anterior,
            status_novo=status_novo,
        )


# ═════════════════════════════════════════════════
# 5. ITEM DO PEDIDO (MANTIDO)
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

    # Campos tributação
    custo_real = models.DecimalField(
        "Custo Real (R$)", max_digits=14, decimal_places=2,
        default=Decimal('0.00'), editable=False,
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
        valor = self.quantidade * self.valor_unitario
        return self.material.calcular_custo_compra(valor, self.quantidade)

    def save(self, *args, **kwargs):
        self.valor_total = self.quantidade * self.valor_unitario
        try:
            calc = self.calcular_impostos()
            self.total_impostos = calc.get('total_impostos', Decimal('0.00'))
            self.total_creditos = calc.get('total_creditos', Decimal('0.00'))
            self.custo_real = calc.get('custo_real', Decimal('0.00'))
        except Exception:
            self.total_impostos = Decimal('0.00')
            self.total_creditos = Decimal('0.00')
            self.custo_real = Decimal('0.00')
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Item do Pedido"
        verbose_name_plural = "Itens do Pedido"
        ordering = ['material__classificacao', 'material__tipo']

    def __str__(self):
        return f"{self.quantidade}x {self.material.descricao}"


# ═════════════════════════════════════════════════════════════════════
# 6. SOLICITAÇÃO DE COMPRA — WORKFLOW PÓS-APROVAÇÃO
# ═════════════════════════════════════════════════════════════════════

def solicitacao_upload_path(instance, filename):
    return f"suprimentos/solicitacoes/{instance.solicitacao.numero}/{filename}"


class SolicitacaoCompra(models.Model):
    """
    Solicitação de compra — gerada automaticamente quando um Pedido é APROVADO.
    Workflow: Fazer Cotação → Cotação Enviada → Criar Pedido/CT →
              Em Aprovação → Enviar Pedido → Entrega Pendente → Concluído
    """

    class StatusChoices(models.TextChoices):
        FAZER_COTACAO = 'FAZER_COTACAO', 'Fazer Cotação'
        COTACAO_ENVIADA = 'COTACAO_ENVIADA', 'Cotação Enviada'
        CRIAR_PEDIDO_CT = 'CRIAR_PEDIDO_CT', 'Criar Pedido/CT'
        EM_APROVACAO = 'EM_APROVACAO', 'Em Aprovação'
        ENVIAR_PEDIDO = 'ENVIAR_PEDIDO', 'Enviar Pedido'
        ENTREGA_PENDENTE = 'ENTREGA_PENDENTE', 'Entrega Pendente'
        CONCLUIDO = 'CONCLUIDO', 'Concluído'
        CANCELADO = 'CANCELADO', 'Cancelado'

    # ───── Identificação ─────
    numero = models.CharField(
        "Nº Solicitação", max_length=30, unique=True, editable=False,
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        verbose_name="Filial", null=True, blank=True,
    )
    status = models.CharField(
        "Status", max_length=25,
        choices=StatusChoices.choices,
        default=StatusChoices.FAZER_COTACAO,
    )

    # ───── Dados herdados do Pedido ─────
    tipo_obra = models.CharField(
        "Tipo de Obra", max_length=2,
        choices=TipoObra.choices,
    )
    contrato = models.ForeignKey(
        Contrato, on_delete=models.PROTECT,
        related_name='solicitacoes_compra',
        verbose_name="Obra (CM / CR / VE)",
    )
    descricao_material = models.TextField("Descrição do Material")
    quantidade = models.DecimalField(
        "Quantidade", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    unidade_medida = models.CharField(
        "Unidade de Medida", max_length=20,
        choices=UnidadeMedida.choices,
        default=UnidadeMedida.UNID,
    )
    tipo_insumo = models.CharField(
        "Tipo de Insumo", max_length=30,
        choices=TipoMaterial.choices,
        blank=True, default='',
    )
    data_necessaria = models.DateField(
        "Data Necessária para Entrega", null=True, blank=True,
    )

    # ───── Responsáveis (TODOS selecionáveis — são funcionários) ─────
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='solicitacoes_compra',
        verbose_name="Solicitante",
    )
    aprovador_inicial = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='solicitacoes_aprovador_inicial',
        verbose_name="Aprovador (Gerente)",
        null=True, blank=True,
        help_text="Gerente que aprovou o pedido original.",
    )
    comprador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='solicitacoes_comprador',
        verbose_name="Comprador Responsável",
        null=True, blank=True,
        help_text="Profissional de Suprimentos responsável pela cotação e compra.",
    )
    aprovador_cotacao = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='solicitacoes_aprovador_cotacao',
        verbose_name="Aprovador da Cotação",
        null=True, blank=True,
    )
    aprovador_pedido = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='solicitacoes_aprovador_pedido',
        verbose_name="Aprovador do Pedido",
        null=True, blank=True,
    )

    # ───── Etapa 1 — Aprovação Inicial ─────
    data_aprovacao_inicial = models.DateTimeField(
        "Data Aprovação Inicial", null=True, blank=True,
    )

    # ───── Etapa 2 — Cotação (Comprador) ─────
    data_cotacao = models.DateField("Data da Cotação", null=True, blank=True)
    numero_cotacao = models.CharField(
        "Nº da Cotação", max_length=50, blank=True, default='',
    )
    cnpj_compra = models.CharField(
        "CNPJ para Compra", max_length=18, blank=True, default='',
    )
    tipo_nota_fiscal = models.CharField(
        "Tipo de Nota Fiscal", max_length=20,
        choices=TipoNotaFiscal.choices,
        blank=True, default='',
    )

    # ───── Etapa 3 — Validação da Cotação ─────
    data_validacao_cotacao = models.DateField(
        "Data da Validação", null=True, blank=True,
    )

    # ───── Etapa 4 — Pedido no Sienge ─────
    data_criacao_pedido = models.DateField(
        "Data Criação do Pedido", null=True, blank=True,
    )
    numero_pedido_sienge = models.CharField(
        "Nº do Pedido (Sienge)", max_length=50, blank=True, default='',
    )
    fornecedor = models.ForeignKey(
        Parceiro, on_delete=models.SET_NULL,
        related_name='solicitacoes_fornecidas',
        verbose_name="Fornecedor", null=True, blank=True,
    )
    valor_pedido = models.DecimalField(
        "Valor do Pedido (R$)", max_digits=14, decimal_places=2,
        null=True, blank=True,
    )

    # ───── Etapa 5 — Aprovação do Pedido ─────
    data_aprovacao_pedido = models.DateField(
        "Data Aprovação do Pedido", null=True, blank=True,
    )

    # ───── Etapa 6 — Envio ao Fornecedor ─────
    data_envio_fornecedor = models.DateField(
        "Data Envio ao Fornecedor", null=True, blank=True,
    )

    # ───── Etapa 7 — Entrega ─────
    data_prevista_entrega = models.DateField(
        "Data Prevista de Entrega", null=True, blank=True,
    )
    data_entrega_efetiva = models.DateField(
        "Data de Entrega Efetiva", null=True, blank=True,
        help_text="Obtida via planilha de rotas do motorista.",
    )

    # ───── Etapa 8 — Encerramento ─────
    numero_nota_fiscal = models.CharField(
        "Nº da Nota Fiscal", max_length=50, blank=True, default='',
    )

    # ───── Observações e Cancelamento ─────
    observacoes = models.TextField(
        "Observações", blank=True, default='',
        help_text="Registro de informações relevantes sobre o processo.",
    )
    motivo_cancelamento = models.TextField(
        "Motivo do Cancelamento", blank=True, default='',
    )

    # ───── Timestamps ─────
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    objects = FilialManager()

    class Meta:
        verbose_name = "Solicitação de Compra"
        verbose_name_plural = "Solicitações de Compra"
        ordering = ['-criado_em']
        permissions = [
            ("pode_executar_cotacao", "Pode executar cotações (Comprador)"),
        ]

    def __str__(self):
        return f"SOL-{self.numero} — {self.descricao_material[:50]}"

    def get_absolute_url(self):
        return reverse('suprimentos:solicitacao_detalhe', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.numero:
            hoje = timezone.now()
            prefix = f"SOL-{hoje.strftime('%Y%m')}"
            ultimo = SolicitacaoCompra.objects.filter(
                numero__startswith=prefix
            ).order_by('-numero').first()
            seq = int(ultimo.numero.split('-')[-1]) + 1 if ultimo else 1
            self.numero = f"{prefix}-{seq:04d}"
        super().save(*args, **kwargs)

    # ───── Verificação de Verba ─────
    def verificar_verba(self):
        if not self.valor_pedido:
            return True, "Valor do pedido ainda não definido."

        ano = self.data_necessaria.year if self.data_necessaria else timezone.now().year
        mes = self.data_necessaria.month if self.data_necessaria else timezone.now().month
        verba = self.contrato.verba_do_mes(ano, mes)

        campo_saldo = 'saldo_consumo'
        cat_label = 'Consumo'
        campo_verba = 'verba_consumo'

        if self.tipo_insumo in ('EPI', 'CREME'):
            campo_saldo = 'saldo_epi'
            campo_verba = 'verba_epi'
            cat_label = 'EPI'

        saldo = getattr(verba, campo_saldo, Decimal('0.00'))
        if self.valor_pedido > saldo:
            return False, (
                f"⚠️ Valor R$ {self.valor_pedido:.2f} excede o saldo de "
                f"{cat_label}: R$ {saldo:.2f} "
                f"(Verba: R$ {getattr(verba, campo_verba):.2f})"
            )
        return True, "Dentro da verba."

    # ───── Helpers de status ─────
    @property
    def status_badge_class(self):
        mapa = {
            'FAZER_COTACAO': 'info',
            'COTACAO_ENVIADA': 'primary',
            'CRIAR_PEDIDO_CT': 'info',
            'EM_APROVACAO': 'warning',
            'ENVIAR_PEDIDO': 'primary',
            'ENTREGA_PENDENTE': 'secondary',
            'CONCLUIDO': 'success',
            'CANCELADO': 'dark',
        }
        return mapa.get(self.status, 'secondary')

    @property
    def etapa_atual(self):
        mapa = {
            'FAZER_COTACAO': 1,
            'COTACAO_ENVIADA': 2,
            'CRIAR_PEDIDO_CT': 3,
            'EM_APROVACAO': 4,
            'ENVIAR_PEDIDO': 5,
            'ENTREGA_PENDENTE': 6,
            'CONCLUIDO': 8,
            'CANCELADO': 0,
        }
        return mapa.get(self.status, 0)

    @property
    def pode_cancelar(self):
        return self.status not in ('CONCLUIDO', 'CANCELADO')

    @property
    def dias_em_aberto(self):
        if self.status == 'CONCLUIDO' and self.data_entrega_efetiva:
            return (self.data_entrega_efetiva - self.criado_em.date()).days
        return (timezone.now().date() - self.criado_em.date()).days


# ═════════════════════════════════════════════════
# 6b. ANEXOS DA SOLICITAÇÃO
# ═════════════════════════════════════════════════

class AnexoSolicitacao(models.Model):
    solicitacao = models.ForeignKey(
        SolicitacaoCompra, on_delete=models.CASCADE,
        related_name='anexos', verbose_name="Solicitação",
    )
    arquivo = models.FileField("Arquivo", upload_to=solicitacao_upload_path)
    descricao = models.CharField("Descrição", max_length=255, blank=True, default='')
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="Enviado por",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Anexo da Solicitação"
        verbose_name_plural = "Anexos da Solicitação"
        ordering = ['-criado_em']

    def __str__(self):
        return f"Anexo: {self.descricao or self.arquivo.name}"

    @property
    def nome_arquivo(self):
        return self.arquivo.name.split('/')[-1] if self.arquivo else ''

    @property
    def extensao(self):
        nome = self.nome_arquivo
        return nome.rsplit('.', 1)[-1].lower() if '.' in nome else ''

    @property
    def is_imagem(self):
        return self.extensao in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp')

    @property
    def is_pdf(self):
        return self.extensao == 'pdf'


# ═════════════════════════════════════════════════
# 6c. HISTÓRICO DA SOLICITAÇÃO
# ═════════════════════════════════════════════════

class HistoricoSolicitacao(models.Model):
    solicitacao = models.ForeignKey(
        SolicitacaoCompra, on_delete=models.CASCADE,
        related_name='historico', verbose_name="Solicitação",
    )
    versao = models.PositiveIntegerField("Versão")
    descricao = models.TextField("Descrição das Alterações")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="Responsável",
    )
    status_anterior = models.CharField(
        "Status Anterior", max_length=25, blank=True, default='',
    )
    status_novo = models.CharField(
        "Status Novo", max_length=25, blank=True, default='',
    )
    criado_em = models.DateTimeField("Data", auto_now_add=True)

    class Meta:
        verbose_name = "Histórico da Solicitação"
        verbose_name_plural = "Histórico das Solicitações"
        ordering = ['-versao']

    def __str__(self):
        return f"v{self.versao} — {self.descricao[:60]}"

    @classmethod
    def registrar(cls, solicitacao, descricao, responsavel,
                  status_anterior='', status_novo=''):
        ultima_versao = cls.objects.filter(
            solicitacao=solicitacao
        ).order_by('-versao').values_list('versao', flat=True).first() or 0
        return cls.objects.create(
            solicitacao=solicitacao,
            versao=ultima_versao + 1,
            descricao=descricao,
            responsavel=responsavel,
            status_anterior=status_anterior,
            status_novo=status_novo,
        )


# ═════════════════════════════════════════════════
# 7. ESTOQUE DE CONSUMO (MANTIDO)
# ═════════════════════════════════════════════════
class EstoqueConsumo(models.Model):
    class TipoMovimento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SAIDA = 'SAIDA', 'Saída'
        AJUSTE = 'AJUSTE', 'Ajuste'

    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name='movimentacoes_consumo', verbose_name="Material",
    )
    contrato = models.ForeignKey(
        Contrato, on_delete=models.PROTECT,
        related_name='estoque_consumo', verbose_name="Contrato",
    )
    tipo = models.CharField("Tipo", max_length=10, choices=TipoMovimento.choices)
    quantidade = models.IntegerField("Quantidade")
    pedido = models.ForeignKey(
        Pedido, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='movimentacoes_estoque', verbose_name="Pedido Origem",
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        verbose_name="Responsável",
    )
    justificativa = models.CharField(
        "Justificativa", max_length=255, blank=True, default='',
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT, verbose_name="Filial",
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

