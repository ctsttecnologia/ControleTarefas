
# tributacao/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from core.upload import UploadPath, delete_old_file, safe_delete_file
from core.validators import SecureFileValidator

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
# 1. NCM
# ══════════════════════════════════════════════════════
class NCM(models.Model):
    codigo = models.CharField(
        "Código NCM", max_length=10, unique=True,
        help_text="Formato: 0000.00.00 — Ex: 8544.49.00"
    )
    descricao = models.CharField("Descrição", max_length=500)
    ex_tipi = models.CharField(
        "Exceção TIPI", max_length=3, blank=True, default="",
    )
    aliquota_ipi_padrao = _pct_field(
        "Alíquota IPI padrão (%)",
        help_text="Alíquota IPI da TIPI"
    )

    # ── Upload seguro: tabela NCM em XML (ex: importação da RFB) ──
    arquivo_xml = models.FileField(
        "Arquivo XML (RFB)",
        upload_to=UploadPath('tributacao'),
        blank=True,
        null=True,
        validators=[SecureFileValidator('tributacao')],
        help_text="XML da Receita Federal com a tabela NCM, se importado manualmente.",
    )

    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "NCM"
        verbose_name_plural = "NCMs"
        ordering = ["codigo"]
        permissions = [
            ("pode_gerenciar_tabelas_fiscais", "Pode gerenciar tabelas fiscais (NCM/CFOP/CST)"),
        ]

    def __str__(self):
        return f"{self.codigo} — {self.descricao[:60]}"

    def save(self, *args, **kwargs):
        delete_old_file(self, 'arquivo_xml')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        safe_delete_file(self, 'arquivo_xml')
        super().delete(*args, **kwargs)


# ══════════════════════════════════════════════════════
# 2. CFOP
# ══════════════════════════════════════════════════════
class CFOP(models.Model):
    TIPO_CHOICES = [
        ("E", "Entrada"),
        ("S", "Saída"),
    ]

    codigo = models.CharField("Código CFOP", max_length=4, unique=True)
    descricao = models.CharField("Descrição", max_length=400)
    tipo = models.CharField("Tipo", max_length=1, choices=TIPO_CHOICES, default="E")
    aplicacao = models.TextField("Aplicação", blank=True, default="")
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "CFOP"
        verbose_name_plural = "CFOPs"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.descricao[:60]}"

    @property
    def is_interestadual(self):
        return self.codigo[0] in ("2", "6")

    @property
    def is_importacao(self):
        return self.codigo[0] in ("3", "7")


# ══════════════════════════════════════════════════════
# 3. CST
# ══════════════════════════════════════════════════════
class CST(models.Model):
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
# 4. GRUPO TRIBUTÁRIO
# ══════════════════════════════════════════════════════
class GrupoTributario(models.Model):
    NATUREZA_CHOICES = [
        ("E", "Entrada (Compra)"),
        ("S", "Saída (Venda/Remessa)"),
    ]

    nome = models.CharField("Nome do Grupo", max_length=200)
    descricao = models.TextField("Descrição", blank=True, default="")
    natureza = models.CharField(
        "Natureza", max_length=1, choices=NATUREZA_CHOICES, default="E"
    )
    cfop = models.ForeignKey(
        CFOP, on_delete=models.PROTECT, verbose_name="CFOP padrão"
    )
    ncm = models.ForeignKey(
        NCM, on_delete=models.SET_NULL,
        verbose_name="NCM padrão", blank=True, null=True,
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
        permissions = [
            ("pode_gerenciar_todas_filiais", "Pode gerenciar grupos tributários de todas as filiais"),
        ]

    def __str__(self):
        return self.nome

    def get_tributacao_federal(self):
        return getattr(self, "tributacao_federal", None)

    def get_tributacao_estadual(self, uf_origem, uf_destino):
        return self.tributacoes_estaduais.filter(
            uf_origem=uf_origem,
            uf_destino=uf_destino,
            ativo=True,
        ).first()

    def calcular_impostos(self, valor_produtos, quantidade=1, uf_origem='SP', uf_destino='SP'):
        from decimal import Decimal, ROUND_HALF_UP

        valor = Decimal(str(valor_produtos))
        qtd = Decimal(str(quantidade)) if quantidade > 0 else Decimal('1')
        ZERO = Decimal('0.00')

        resultado = {
            'valor_produtos': valor,
            'sem_grupo': False,
            'icms':     {'aliquota': ZERO, 'valor': ZERO, 'recuperavel': False, 'base': ZERO},
            'icms_st':  {'aliquota': ZERO, 'valor': ZERO, 'mva': ZERO},
            'fcp':      {'aliquota': ZERO, 'valor': ZERO},
            'ipi':      {'aliquota': ZERO, 'valor': ZERO, 'recuperavel': False},
            'pis':      {'aliquota': ZERO, 'valor': ZERO, 'recuperavel': False},
            'cofins':   {'aliquota': ZERO, 'valor': ZERO, 'recuperavel': False},
            'total_impostos':      ZERO,
            'total_creditos':      ZERO,
            'total_nfe':           ZERO,
            'custo_real':          ZERO,
            'custo_unitario':      ZERO,
            'percentual_economia': ZERO,
        }

        # ── Federal ──────────────────────────────────
        try:
            federal = self.tributacao_federal
        except TributacaoFederal.DoesNotExist:
            federal = None

        if federal:
            ipi_aliq  = federal.aliquota_ipi or ZERO
            ipi_valor = (valor * ipi_aliq / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            resultado['ipi'] = {'aliquota': ipi_aliq, 'valor': ipi_valor, 'recuperavel': False}

            pis_aliq  = federal.aliquota_pis or ZERO
            pis_valor = (valor * pis_aliq / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            resultado['pis'] = {
                'aliquota': pis_aliq,
                'valor': pis_valor,
                'recuperavel': federal.gera_credito_pis,
            }

            cofins_aliq  = federal.aliquota_cofins or ZERO
            cofins_valor = (valor * cofins_aliq / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            resultado['cofins'] = {
                'aliquota': cofins_aliq,
                'valor': cofins_valor,
                'recuperavel': federal.gera_credito_cofins,
            }

        # ── Estadual ─────────────────────────────────
        estadual = self.tributacoes_estaduais.filter(
            uf_origem=uf_origem, uf_destino=uf_destino, ativo=True,
        ).first()

        if estadual:
            icms_aliq  = estadual.aliquota_icms or ZERO
            reducao    = estadual.reducao_base_icms or ZERO
            base_icms  = valor * (1 - reducao / 100)
            icms_valor = (base_icms * icms_aliq / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            resultado['icms'] = {
                'aliquota': icms_aliq,
                'valor': icms_valor,
                'recuperavel': estadual.permite_credito,
                'base': base_icms.quantize(Decimal('0.01')),
            }

            if estadual.tem_st:
                mva          = estadual.mva or ZERO
                icms_st_aliq = estadual.aliquota_icms_st or ZERO
                base_st      = valor * (1 + mva / 100)
                icms_st_val  = (base_st * icms_st_aliq / 100 - icms_valor).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                resultado['icms_st'] = {
                    'aliquota': icms_st_aliq,
                    'valor': max(icms_st_val, ZERO),
                    'mva': mva,
                }

            fcp_aliq  = estadual.aliquota_fcp or ZERO
            fcp_valor = (valor * fcp_aliq / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            resultado['fcp'] = {'aliquota': fcp_aliq, 'valor': fcp_valor}

        # ── Totais ────────────────────────────────────
        total_impostos = sum([
            resultado['ipi']['valor'],
            resultado['pis']['valor'],
            resultado['cofins']['valor'],
            resultado['icms']['valor'],
            resultado['icms_st']['valor'],
            resultado['fcp']['valor'],
        ])

        total_creditos = sum(
            resultado[t]['valor']
            for t in ('icms', 'ipi', 'pis', 'cofins')
            if resultado[t]['recuperavel']
        )

        total_nfe  = valor + resultado['ipi']['valor'] + resultado['icms_st']['valor'] + resultado['fcp']['valor']
        custo_real = (total_nfe - total_creditos).quantize(Decimal('0.01'))
        custo_unitario = (custo_real / qtd).quantize(Decimal('0.01'))
        percentual_economia = (
            (total_creditos / total_nfe * 100).quantize(Decimal('0.01'))
            if total_nfe > 0 else ZERO
        )

        resultado.update({
            'total_impostos':      total_impostos,
            'total_creditos':      total_creditos,
            'total_nfe':           total_nfe,
            'custo_real':          custo_real,
            'custo_unitario':      custo_unitario,
            'percentual_economia': percentual_economia,
        })
        return resultado


# ══════════════════════════════════════════════════════
# 5. TRIBUTAÇÃO FEDERAL
# ══════════════════════════════════════════════════════
class TributacaoFederal(models.Model):
    grupo = models.OneToOneField(
        GrupoTributario,
        on_delete=models.CASCADE,
        related_name="tributacao_federal",
        verbose_name="Grupo Tributário"
    )

    cst_ipi = models.ForeignKey(
        CST, on_delete=models.PROTECT, verbose_name="CST IPI",
        related_name="+", blank=True, null=True,
        limit_choices_to={"tipo__startswith": "IPI"}
    )
    aliquota_ipi = _pct_field("Alíquota IPI (%)")

    cst_pis = models.ForeignKey(
        CST, on_delete=models.PROTECT, verbose_name="CST PIS",
        related_name="+", blank=True, null=True,
        limit_choices_to={"tipo": "PIS"}
    )
    aliquota_pis        = _pct_field("Alíquota PIS (%)", default=1.65)
    gera_credito_pis    = models.BooleanField("Gera crédito de PIS?", default=True)

    cst_cofins = models.ForeignKey(
        CST, on_delete=models.PROTECT, verbose_name="CST COFINS",
        related_name="+", blank=True, null=True,
        limit_choices_to={"tipo": "COFINS"}
    )
    aliquota_cofins     = _pct_field("Alíquota COFINS (%)", default=7.60)
    gera_credito_cofins = models.BooleanField("Gera crédito de COFINS?", default=True)

    # ── Upload seguro: laudo / memorando fiscal em PDF ──
    documento_fiscal = models.FileField(
        "Documento Fiscal (PDF)",
        upload_to=UploadPath('tributacao'),
        blank=True,
        null=True,
        validators=[SecureFileValidator('tributacao')],
        help_text="Laudo, parecer ou memorando fiscal em PDF ou XML.",
    )

    observacoes = models.TextField("Observações", blank=True, default="")

    class Meta:
        verbose_name = "Tributação Federal"
        verbose_name_plural = "Tributações Federais"

    def __str__(self):
        return f"Federal — {self.grupo.nome}"

    @property
    def total_creditos_percentual(self):
        total = 0
        if self.gera_credito_pis:
            total += self.aliquota_pis
        if self.gera_credito_cofins:
            total += self.aliquota_cofins
        return total

    def save(self, *args, **kwargs):
        delete_old_file(self, 'documento_fiscal')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        safe_delete_file(self, 'documento_fiscal')
        super().delete(*args, **kwargs)


# ══════════════════════════════════════════════════════
# 6. TRIBUTAÇÃO ESTADUAL
# ══════════════════════════════════════════════════════
class TributacaoEstadual(models.Model):
    grupo = models.ForeignKey(
        GrupoTributario,
        on_delete=models.CASCADE,
        related_name="tributacoes_estaduais",
        verbose_name="Grupo Tributário"
    )
    uf_origem  = models.CharField("UF Origem",  max_length=2, choices=UF_CHOICES)
    uf_destino = models.CharField("UF Destino", max_length=2, choices=UF_CHOICES)

    cst_icms = models.ForeignKey(
        CST, on_delete=models.PROTECT, verbose_name="CST ICMS",
        related_name="+", blank=True, null=True,
        limit_choices_to={"tipo": "ICMS"}
    )
    aliquota_icms      = _pct_field("Alíquota ICMS (%)")
    reducao_base_icms  = _pct_field("Redução de Base ICMS (%)")
    permite_credito    = models.BooleanField("Permite crédito de ICMS?", default=False)

    tem_st         = models.BooleanField("Tem ICMS-ST?", default=False)
    mva            = _pct_field("MVA (%)")
    aliquota_icms_st = _pct_field("Alíquota ICMS-ST (%)")
    aliquota_fcp   = _pct_field("Alíquota FCP (%)")

    ativo       = models.BooleanField("Ativo", default=True)
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

