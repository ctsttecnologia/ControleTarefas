
# tributacao/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# ══════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════
UF_CHOICES = [
    ("AC", "Acre"), ("AL", "Alagoas"), ("AM", "Amazonas"), ("AP", "Amapá"),
    ("BA", "Bahia"), ("CE", "Ceará"), ("DF", "Distrito Federal"),
    ("ES", "Espírito Santo"), ("GO", "Goiás"), ("MA", "Maranhão"),
    ("MG", "Minas Gerais"), ("MS", "Mato Grosso do Sul"),
    ("MT", "Mato Grosso"), ("PA", "Pará"), ("PB", "Paraíba"),
    ("PE", "Pernambuco"), ("PI", "Piauí"), ("PR", "Paraná"),
    ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
    ("RO", "Rondônia"), ("RR", "Roraima"), ("RS", "Rio Grande do Sul"),
    ("SC", "Santa Catarina"), ("SE", "Sergipe"), ("SP", "São Paulo"),
    ("TO", "Tocantins"),
]

PERCENTUAL_VALIDATORS = [MinValueValidator(0), MaxValueValidator(100)]


def _pct_field(verbose, default=0, help_text=""):
    """Atalho para criar campos de percentual."""
    return models.DecimalField(
        verbose_name=verbose,
        max_digits=5, decimal_places=2, default=default,
        validators=PERCENTUAL_VALIDATORS,
        help_text=help_text,
    )


# ══════════════════════════════════════════════════════
# 1. NCM — Nomenclatura Comum do Mercosul
# ══════════════════════════════════════════════════════
class NCM(models.Model):
    """
    Tabela federal de classificação fiscal de mercadorias.
    Cada produto do suprimentos aponta para um NCM.
    """
    codigo = models.CharField(
        "Código NCM", max_length=10, unique=True,
        help_text="Formato: 0000.00.00 — Ex: 8544.49.00"
    )
    descricao = models.CharField("Descrição", max_length=500)
    ex_tipi = models.CharField(
        "Exceção TIPI", max_length=3, blank=True, default="",
        help_text="Exceção da TIPI, se houver"
    )
    aliquota_ipi_padrao = _pct_field(
        "Alíquota IPI padrão (%)",
        help_text="Alíquota IPI da TIPI — pode ser sobrescrita no Grupo Tributário"
    )
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "NCM"
        verbose_name_plural = "NCMs"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.descricao[:60]}"


# ══════════════════════════════════════════════════════
# 2. CFOP — Código Fiscal de Operações e Prestações
# ══════════════════════════════════════════════════════
class CFOP(models.Model):
    """
    Define a natureza da operação fiscal (entrada/saída, estadual/interestadual).
    """
    TIPO_CHOICES = [
        ("E", "Entrada"),
        ("S", "Saída"),
    ]

    codigo = models.CharField("Código CFOP", max_length=4, unique=True)
    descricao = models.CharField("Descrição", max_length=400)
    tipo = models.CharField("Tipo", max_length=1, choices=TIPO_CHOICES, default="E")
    aplicacao = models.TextField(
        "Aplicação", blank=True, default="",
        help_text="Quando usar este CFOP"
    )
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "CFOP"
        verbose_name_plural = "CFOPs"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.descricao[:60]}"

    @property
    def is_interestadual(self):
        """CFOPs 2.xxx e 6.xxx = interestadual."""
        return self.codigo[0] in ("2", "6")

    @property
    def is_importacao(self):
        """CFOPs 3.xxx e 7.xxx = importação/exportação."""
        return self.codigo[0] in ("3", "7")


# ══════════════════════════════════════════════════════
# 3. CST — Código de Situação Tributária
# ══════════════════════════════════════════════════════
class CST(models.Model):
    """
    Tabela unificada de CSTs para todos os tributos.
    """
    TIPO_CHOICES = [
        ("ICMS", "CST ICMS — Regime Normal"),
        ("IPI_E", "CST IPI — Entrada"),
        ("IPI_S", "CST IPI — Saída"),
        ("PIS", "CST PIS"),
        ("COFINS", "CST COFINS"),
    ]

    tipo = models.CharField("Tipo", max_length=6, choices=TIPO_CHOICES)
    codigo = models.CharField("Código", max_length=3)
    descricao = models.CharField("Descrição", max_length=300)

    class Meta:
        verbose_name = "CST"
        verbose_name_plural = "CSTs"
        unique_together = ("tipo", "codigo")
        ordering = ["tipo", "codigo"]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.codigo} — {self.descricao[:50]}"


# ══════════════════════════════════════════════════════
# 4. GRUPO TRIBUTÁRIO — O perfil fiscal
# ══════════════════════════════════════════════════════
class GrupoTributario(models.Model):
    """
    Agrupa todas as regras fiscais de um tipo de material.
    O Produto do suprimentos aponta para cá.

    Exemplos:
        - "Material Elétrico — Entrada Interna SP"
        - "Material Hidráulico — Entrada Interestadual MG→SP"
        - "Material de Consumo Genérico"
    """
    NATUREZA_CHOICES = [
        ("E", "Entrada (Compra)"),
        ("S", "Saída (Venda/Remessa)"),
    ]

    nome = models.CharField(
        "Nome do Grupo", max_length=200,
        help_text="Ex: Material Elétrico — Entrada SP"
    )
    descricao = models.TextField("Descrição", blank=True, default="")
    natureza = models.CharField(
        "Natureza", max_length=1,
        choices=NATUREZA_CHOICES, default="E"
    )
    cfop = models.ForeignKey(
        CFOP, on_delete=models.PROTECT,
        verbose_name="CFOP padrão",
        help_text="CFOP padrão para este grupo"
    )
    ncm = models.ForeignKey(
        NCM, on_delete=models.SET_NULL,
        verbose_name="NCM padrão",
        blank=True, null=True,
        help_text="Deixe vazio se o grupo for genérico"
    )
    filial = models.ForeignKey(
        "usuario.Filial",
        on_delete=models.CASCADE,
        related_name="grupos_tributarios",
        verbose_name="Filial"
    )
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Grupo Tributário"
        verbose_name_plural = "Grupos Tributários"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def get_tributacao_federal(self):
        """Retorna a tributação federal vinculada (OneToOne)."""
        return getattr(self, "tributacao_federal", None)

    def get_tributacao_estadual(self, uf_origem, uf_destino):
        """Retorna a tributação estadual para o par de UFs."""
        return self.tributacoes_estaduais.filter(
            uf_origem=uf_origem,
            uf_destino=uf_destino,
            ativo=True,
        ).first()

    def calcular_impostos(self, valor_produtos, quantidade=1):
        """
        Calcula todos os impostos sobre um valor de compra.
        Retorna dict com valores, créditos e custo real.
        """
        from decimal import Decimal, ROUND_HALF_UP
        D = Decimal

        valor = D(str(valor_produtos))
        zero = D("0.00")

        if valor <= 0:
            return {
                "valor_produtos": zero,
                "quantidade": quantidade,
                "ipi_valor": zero, "ipi_credito": zero, "ipi_custo": zero,
                "ipi_aliquota": self.ipi_aliquota, "ipi_recuperavel": self.ipi_recuperavel,
                "pis_valor": zero, "pis_credito": zero,
                "pis_aliquota": self.pis_aliquota, "pis_recuperavel": self.pis_recuperavel,
                "cofins_valor": zero, "cofins_credito": zero,
                "cofins_aliquota": self.cofins_aliquota, "cofins_recuperavel": self.cofins_recuperavel,
                "icms_valor": zero, "icms_credito": zero,
                "icms_aliquota": self.icms_aliquota, "icms_reducao_base": self.icms_reducao_base,
                "icms_recuperavel": self.icms_recuperavel,
                "icms_st_valor": zero, "icms_st_aliquota": self.icms_st_aliquota,
                "icms_st_mva": self.icms_st_mva,
                "total_impostos": zero, "total_creditos": zero,
                "total_nfe": zero, "custo_real": zero,
                "custo_unitario": zero, "percentual_economia": zero,
            }

        def q(v):
            return v.quantize(D("0.01"), ROUND_HALF_UP)

        # ─── IPI (incide sobre valor dos produtos, compõe NF-e) ───
        ipi_valor = q(valor * self.ipi_aliquota / 100)
        ipi_credito = ipi_valor if self.ipi_recuperavel else zero
        ipi_custo = zero if self.ipi_recuperavel else ipi_valor

        # ─── PIS (incide sobre valor dos produtos) ───
        pis_valor = q(valor * self.pis_aliquota / 100)
        pis_credito = pis_valor if self.pis_recuperavel else zero

        # ─── COFINS (incide sobre valor dos produtos) ───
        cofins_valor = q(valor * self.cofins_aliquota / 100)
        cofins_credito = cofins_valor if self.cofins_recuperavel else zero

        # ─── ICMS (sobre valor dos produtos com possível redução de base) ───
        base_icms = valor * (1 - self.icms_reducao_base / 100)
        icms_valor = q(base_icms * self.icms_aliquota / 100)
        icms_credito = icms_valor if self.icms_recuperavel else zero

        # ─── ICMS-ST (Substituição Tributária) ───
        icms_st_valor = zero
        if self.icms_st_aliquota > 0 and self.icms_st_mva > 0:
            base_st = (valor + ipi_valor) * (1 + self.icms_st_mva / 100)
            icms_st_bruto = q(base_st * self.icms_st_aliquota / 100)
            icms_st_valor = max(icms_st_bruto - icms_valor, zero)

        # ─── Totais ───
        total_impostos = ipi_valor + pis_valor + cofins_valor + icms_valor + icms_st_valor
        total_creditos = ipi_credito + pis_credito + cofins_credito + icms_credito

        # Valor da NF-e = produtos + IPI (se não recuperável) + ICMS-ST
        total_nfe = valor + ipi_custo + icms_st_valor
        custo_real = total_nfe - total_creditos

        qtd = D(str(quantidade)) if quantidade > 0 else D("1")

        return {
            "valor_produtos": valor,
            "quantidade": quantidade,

            "ipi_aliquota": self.ipi_aliquota,
            "ipi_valor": ipi_valor,
            "ipi_credito": ipi_credito,
            "ipi_custo": ipi_custo,
            "ipi_recuperavel": self.ipi_recuperavel,

            "pis_aliquota": self.pis_aliquota,
            "pis_valor": pis_valor,
            "pis_credito": pis_credito,
            "pis_recuperavel": self.pis_recuperavel,

            "cofins_aliquota": self.cofins_aliquota,
            "cofins_valor": cofins_valor,
            "cofins_credito": cofins_credito,
            "cofins_recuperavel": self.cofins_recuperavel,

            "icms_aliquota": self.icms_aliquota,
            "icms_reducao_base": self.icms_reducao_base,
            "icms_valor": icms_valor,
            "icms_credito": icms_credito,
            "icms_recuperavel": self.icms_recuperavel,

            "icms_st_aliquota": self.icms_st_aliquota,
            "icms_st_mva": self.icms_st_mva,
            "icms_st_valor": icms_st_valor,

            "total_impostos": total_impostos,
            "total_creditos": total_creditos,
            "total_nfe": total_nfe,
            "custo_real": custo_real,
            "custo_unitario": q(custo_real / qtd),
            "percentual_economia": q(total_creditos / total_nfe * 100) if total_nfe > 0 else zero,
        }


# ══════════════════════════════════════════════════════
# 5. TRIBUTAÇÃO FEDERAL — IPI, PIS, COFINS
# ══════════════════════════════════════════════════════
class TributacaoFederal(models.Model):
    """
    Tributos federais vinculados a um Grupo Tributário.
    Relação 1:1 com GrupoTributario.
    """
    grupo = models.OneToOneField(
        GrupoTributario,
        on_delete=models.CASCADE,
        related_name="tributacao_federal",
        verbose_name="Grupo Tributário"
    )

    # ── IPI ──
    cst_ipi = models.ForeignKey(
        CST, on_delete=models.PROTECT,
        verbose_name="CST IPI",
        related_name="+",
        blank=True, null=True,
        limit_choices_to={"tipo__startswith": "IPI"}
    )
    aliquota_ipi = _pct_field("Alíquota IPI (%)")

    # ── PIS (não-cumulativo → Lucro Real) ──
    cst_pis = models.ForeignKey(
        CST, on_delete=models.PROTECT,
        verbose_name="CST PIS",
        related_name="+",
        blank=True, null=True,
        limit_choices_to={"tipo": "PIS"}
    )
    aliquota_pis = _pct_field("Alíquota PIS (%)", default=1.65)
    gera_credito_pis = models.BooleanField(
        "Gera crédito de PIS?", default=True,
        help_text="Lucro Real não-cumulativo: insumos para serviço geram crédito"
    )

    # ── COFINS (não-cumulativo → Lucro Real) ──
    cst_cofins = models.ForeignKey(
        CST, on_delete=models.PROTECT,
        verbose_name="CST COFINS",
        related_name="+",
        blank=True, null=True,
        limit_choices_to={"tipo": "COFINS"}
    )
    aliquota_cofins = _pct_field("Alíquota COFINS (%)", default=7.60)
    gera_credito_cofins = models.BooleanField(
        "Gera crédito de COFINS?", default=True,
        help_text="Lucro Real não-cumulativo: insumos para serviço geram crédito"
    )

    # ── Observações ──
    observacoes = models.TextField("Observações", blank=True, default="")

    class Meta:
        verbose_name = "Tributação Federal"
        verbose_name_plural = "Tributações Federais"

    def __str__(self):
        return f"Federal — {self.grupo.nome}"

    @property
    def total_creditos_percentual(self):
        """Soma das alíquotas que geram crédito."""
        total = 0
        if self.gera_credito_pis:
            total += self.aliquota_pis
        if self.gera_credito_cofins:
            total += self.aliquota_cofins
        return total


# ══════════════════════════════════════════════════════
# 6. TRIBUTAÇÃO ESTADUAL — ICMS (por par de UF)
# ══════════════════════════════════════════════════════
class TributacaoEstadual(models.Model):
    """
    Tributação ICMS para cada combinação UF origem → UF destino.
    Um GrupoTributario pode ter VÁRIAS tributações estaduais
    (uma por par de UFs onde a empresa opera).
    """
    grupo = models.ForeignKey(
        GrupoTributario,
        on_delete=models.CASCADE,
        related_name="tributacoes_estaduais",
        verbose_name="Grupo Tributário"
    )
    uf_origem = models.CharField(
        "UF Origem", max_length=2, choices=UF_CHOICES,
        help_text="Estado do fornecedor"
    )
    uf_destino = models.CharField(
        "UF Destino", max_length=2, choices=UF_CHOICES,
        help_text="Estado da filial (destino da compra)"
    )

    # ── ICMS ──
    cst_icms = models.ForeignKey(
        CST, on_delete=models.PROTECT,
        verbose_name="CST ICMS",
        related_name="+",
        blank=True, null=True,
        limit_choices_to={"tipo": "ICMS"}
    )
    aliquota_icms = _pct_field(
        "Alíquota ICMS (%)",
        help_text="Interna: 18% (SP), 17% (maioria). Interestadual: 7% ou 12%"
    )
    reducao_base_icms = _pct_field(
        "Redução de Base ICMS (%)",
        help_text="Alguns produtos têm base de cálculo reduzida"
    )
    permite_credito = models.BooleanField(
        "Permite crédito de ICMS?", default=False,
        help_text="Material para uso/consumo em serviço: geralmente NÃO permite crédito. "
                  "Verifique a legislação do estado."
    )

    # ── ICMS-ST (Substituição Tributária) ──
    tem_st = models.BooleanField("Tem ICMS-ST?", default=False)
    mva = _pct_field(
        "MVA (%)",
        help_text="Margem de Valor Agregado para ST"
    )
    aliquota_icms_st = _pct_field("Alíquota ICMS-ST (%)")

    # ── FCP (Fundo de Combate à Pobreza) ──
    aliquota_fcp = _pct_field(
        "Alíquota FCP (%)",
        help_text="Fundo de Combate à Pobreza — varia por UF (0% a 4%)"
    )

    # ── Controle ──
    ativo = models.BooleanField("Ativo", default=True)
    observacoes = models.TextField("Observações", blank=True, default="")

    class Meta:
        verbose_name = "Tributação Estadual"
        verbose_name_plural = "Tributações Estaduais"
        unique_together = ("grupo", "uf_origem", "uf_destino")
        ordering = ["uf_origem", "uf_destino"]

    def __str__(self):
        return f"ICMS {self.uf_origem}→{self.uf_destino} — {self.grupo.nome}"

    @property
    def is_interestadual(self):
        return self.uf_origem != self.uf_destino

