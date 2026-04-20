
# automovel/models.py

from django import forms
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.managers import FilialManager
from core.upload import make_upload_path
from core.validators import SecureImageValidator
from usuario.models import Filial
from datetime import date


# ═════════════════════════════════════════════════════════════════════════════
# CLASSE BASE ABSTRATA
# ═════════════════════════════════════════════════════════════════════════════

class BaseFilialModel(models.Model):
    """Modelo abstrato que adiciona o campo 'filial' e o manager padrão."""

    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="%(class)s_set",
    )
    objects = FilialManager()

    class Meta:
        abstract = True


# ═════════════════════════════════════════════════════════════════════════════
# CARRO
# ═════════════════════════════════════════════════════════════════════════════

class Carro(BaseFilialModel):
    placa = models.CharField(max_length=10, unique=True)
    modelo = models.CharField(max_length=50)
    marca = models.CharField(max_length=50)
    cor = models.CharField(max_length=30)
    ano = models.PositiveIntegerField()
    renavan = models.CharField(max_length=20, unique=True)
    quilometragem = models.PositiveIntegerField(
        default=0, verbose_name=_("Quilometragem"),
    )
    data_ultima_manutencao = models.DateField(null=True, blank=True)
    data_proxima_manutencao = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, null=True)
    disponivel = models.BooleanField(default=True)

    # ── Upload seguro — Foto do Carro ────────────────────────────────────────
    foto = models.ImageField(
        _("Foto do Carro"),
        upload_to=make_upload_path("automovel_foto"),
        validators=[SecureImageValidator("automovel_foto")],
        null=True,
        blank=True,
        help_text=_("Imagem JPG, PNG ou WebP (máx. 4 MB)."),
    )

    @property
    def status_manutencao(self):
        if not self.data_proxima_manutencao:
            return ("indefinido", "Sem data de próxima manutenção definida", "secondary")

        hoje = date.today()
        dias_restantes = (self.data_proxima_manutencao - hoje).days

        if dias_restantes < 0:
            return ("vencido", f"Manutenção vencida há {-dias_restantes} dias!", "danger")
        elif dias_restantes == 0:
            return ("proximo", "Manutenção vence hoje!", "warning")
        elif dias_restantes == 1:
            return ("proximo", "Manutenção vence amanhã!", "warning")
        elif dias_restantes <= 30:
            return ("proximo", f"Manutenção vence em {dias_restantes} dias.", "warning")
        else:
            return ("ok", "Manutenção em dia", "success")

    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placa}"

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        from core.upload import sanitize_image, delete_old_file

        if self.pk:
            delete_old_file(self, "foto")

        super().save(*args, **kwargs)

        if self.foto:
            sanitize_image(self.foto.path)

    def delete(self, *args, **kwargs):
        from core.upload import safe_delete_file

        safe_delete_file(self, "foto")
        super().delete(*args, **kwargs)

    class Meta:
        db_table = "carro"
        verbose_name = _("Carro")
        verbose_name_plural = _("Carros")
        ordering = ["marca", "modelo"]
        permissions = [
            ("view_all_automovel", "Pode ver todos os registros de automóveis da filial"),
        ]


# ═════════════════════════════════════════════════════════════════════════════
# AGENDAMENTO
# ═════════════════════════════════════════════════════════════════════════════

class Carro_agendamento(BaseFilialModel):
    STATUS_CHOICES = [
        ("agendado", "Agendado"),
        ("em_andamento", "Em Andamento"),
        ("finalizado", "Finalizado"),
        ("manutencao", "Em Manutenção"),
        ("cancelado", "Cancelado"),
    ]

    funcionario = models.CharField(max_length=100)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
    )
    carro = models.ForeignKey(
        Carro, on_delete=models.PROTECT, related_name="agendamentos",
    )
    data_hora_agenda = models.DateTimeField()
    data_hora_devolucao = models.DateTimeField()
    cm = models.CharField(max_length=4, verbose_name=_("CM/Contrato"))
    descricao = models.TextField()
    pedagio = models.BooleanField(default=False)
    abastecimento = models.BooleanField(default=False)
    km_inicial = models.PositiveIntegerField()
    km_final = models.PositiveIntegerField(null=True, blank=True)

    # ── Upload seguro — Foto principal ───────────────────────────────────────
    foto_principal = models.ImageField(
        _("Foto Principal"),
        upload_to=make_upload_path("automovel_agendamento"),
        validators=[SecureImageValidator("automovel_agendamento")],
        null=True,
        blank=True,
        help_text=_("Imagem JPG, PNG ou WebP (máx. 5 MB)."),
    )

    assinatura = models.TextField(
        blank=True, null=True, verbose_name=_("Assinatura Digital"),
    )
    responsavel = models.CharField(max_length=100)
    ocorrencia = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="agendado",
    )
    cancelar_agenda = models.BooleanField(default=False)
    motivo_cancelamento = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Agendamento #{self.id} - {self.carro.placa} para {self.funcionario}"

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        from core.upload import sanitize_image, delete_old_file

        if self.pk:
            delete_old_file(self, "foto_principal")

        super().save(*args, **kwargs)

        if self.foto_principal:
            sanitize_image(self.foto_principal.path)

    def delete(self, *args, **kwargs):
        from core.upload import safe_delete_file

        safe_delete_file(self, "foto_principal")
        super().delete(*args, **kwargs)

    class Meta:
        db_table = "carro_agendamento"
        verbose_name = _("Agendamento")
        verbose_name_plural = _("Agendamentos")
        ordering = ["-data_hora_agenda"]

    @property
    def checklist_saida(self):
        return self.checklists.filter(tipo="saida").first()

    @property
    def checklist_retorno(self):
        return self.checklists.filter(tipo="retorno").first()


# ═════════════════════════════════════════════════════════════════════════════
# CHECKLIST
# ═════════════════════════════════════════════════════════════════════════════

class Carro_checklist(BaseFilialModel):
    TIPO_CHOICES = [
        ("saida", "Saída"),
        ("retorno", "Retorno"),
        ("vistoria", "Vistoria"),
    ]
    STATUS_CHOICES = [
        ("ok", "OK"),
        ("danificado", "Danificado"),
        ("nao_aplicavel", "Não Aplicável"),
    ]

    agendamento = models.ForeignKey(
        Carro_agendamento, on_delete=models.CASCADE, related_name="checklists",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    data_hora = models.DateTimeField(
        default=timezone.now, verbose_name=_("Data/Hora"),
    )

    # ── Revisão Frontal ─────────────────────────────────────────────────────
    revisao_frontal_status = models.CharField(
        max_length=15, choices=STATUS_CHOICES,
    )
    foto_frontal = models.ImageField(
        _("Foto Frontal"),
        upload_to=make_upload_path("automovel_checklist"),
        validators=[SecureImageValidator("automovel_checklist")],
        help_text=_("Imagem JPG, PNG ou WebP (máx. 5 MB)."),
    )

    # ── Revisão Traseira ─────────────────────────────────────────────────────
    revisao_trazeira_status = models.CharField(
        max_length=15, choices=STATUS_CHOICES,
    )
    foto_trazeira = models.ImageField(
        _("Foto Traseira"),
        upload_to=make_upload_path("automovel_checklist"),
        validators=[SecureImageValidator("automovel_checklist")],
        help_text=_("Imagem JPG, PNG ou WebP (máx. 5 MB)."),
    )

    # ── Revisão Lado Motorista ───────────────────────────────────────────────
    revisao_lado_motorista_status = models.CharField(
        max_length=15, choices=STATUS_CHOICES,
    )
    foto_lado_motorista = models.ImageField(
        _("Foto Lado Motorista"),
        upload_to=make_upload_path("automovel_checklist"),
        validators=[SecureImageValidator("automovel_checklist")],
        help_text=_("Imagem JPG, PNG ou WebP (máx. 5 MB)."),
    )

    # ── Revisão Lado Passageiro ──────────────────────────────────────────────
    revisao_lado_passageiro_status = models.CharField(
        max_length=15, choices=STATUS_CHOICES,
    )
    foto_lado_passageiro = models.ImageField(
        _("Foto Lado Passageiro"),
        upload_to=make_upload_path("automovel_checklist"),
        validators=[SecureImageValidator("automovel_checklist")],
        help_text=_("Imagem JPG, PNG ou WebP (máx. 5 MB)."),
    )

    observacoes_gerais = models.TextField(blank=True, null=True)
    assinatura = models.TextField(
        blank=True, null=True, verbose_name=_("Assinatura Digital"),
    )
    confirmacao = models.BooleanField(default=False)

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        from core.upload import sanitize_image, delete_old_file

        campos_foto = [
            "foto_frontal",
            "foto_trazeira",
            "foto_lado_motorista",
            "foto_lado_passageiro",
        ]

        # Remove arquivos antigos ao substituir
        if self.pk:
            for campo in campos_foto:
                delete_old_file(self, campo)

        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Sanitiza todas as imagens
        for campo in campos_foto:
            arquivo = getattr(self, campo, None)
            if arquivo:
                sanitize_image(arquivo.path)

        # Lógica de status do agendamento
        if is_new:
            agendamento = self.agendamento

            if self.tipo == "saida":
                agendamento.status = "em_andamento"
                agendamento.save(update_fields=["status"])

            elif self.tipo == "retorno":
                carro = agendamento.carro
                agendamento.status = "finalizado"

                if agendamento.km_final:
                    carro.quilometragem = agendamento.km_final
                    carro.save(update_fields=["quilometragem"])

                agendamento.save(update_fields=["status"])

    def delete(self, *args, **kwargs):
        from core.upload import safe_delete_file

        for campo in ["foto_frontal", "foto_trazeira", "foto_lado_motorista", "foto_lado_passageiro"]:
            safe_delete_file(self, campo)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Checklist ({self.get_tipo_display()}) para Agendamento #{self.agendamento.id}"

    class Meta:
        db_table = "carro_checklist"
        verbose_name = _("Checklist")
        verbose_name_plural = _("Checklists")
        ordering = ["-data_hora"]
        unique_together = ("agendamento", "tipo")


# ═════════════════════════════════════════════════════════════════════════════
# FOTO (AGENDAMENTO)
# ═════════════════════════════════════════════════════════════════════════════

class Carro_foto(BaseFilialModel):
    agendamento = models.ForeignKey(
        Carro_agendamento, on_delete=models.CASCADE,
        related_name="fotos_agendamento",
    )

    # ── Upload seguro — Imagem ───────────────────────────────────────────────
    imagem = models.ImageField(
        _("Foto"),
        upload_to=make_upload_path("automovel_foto_agendamento"),
        validators=[SecureImageValidator("automovel_foto_agendamento")],
        help_text=_("Imagem JPG, PNG ou WebP (máx. 5 MB)."),
    )

    data_criacao = models.DateTimeField(default=timezone.now)
    observacao = models.TextField(blank=True, null=True)

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        from core.upload import sanitize_image, delete_old_file

        if self.pk:
            delete_old_file(self, "imagem")

        super().save(*args, **kwargs)

        if self.imagem:
            sanitize_image(self.imagem.path)

    def delete(self, *args, **kwargs):
        from core.upload import safe_delete_file

        safe_delete_file(self, "imagem")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Foto #{self.id} - {self.agendamento}"

    class Meta:
        db_table = "carro_foto"
        verbose_name = _("Foto")
        verbose_name_plural = _("Fotos")
        ordering = ["-data_criacao"]
        unique_together = ("agendamento", "imagem")


# ═════════════════════════════════════════════════════════════════════════════
# RASTREAMENTO
# ═════════════════════════════════════════════════════════════════════════════

class Carro_rastreamento(BaseFilialModel):
    agendamento = models.ForeignKey(
        Carro_agendamento, on_delete=models.CASCADE,
        related_name="rastreamentos",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    velocidade = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
    )
    data_hora = models.DateTimeField(default=timezone.now)
    endereco_aproximado = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "carro_rastreamento"
        verbose_name = _("Rastreamento")
        verbose_name_plural = _("Rastreamentos")
        ordering = ["-data_hora"]


# ═════════════════════════════════════════════════════════════════════════════
# MANUTENÇÃO
# ═════════════════════════════════════════════════════════════════════════════

class Carro_manutencao(BaseFilialModel):
    TIPO_CHOICES = [
        ("preventiva", "Preventiva"),
        ("corretiva", "Corretiva"),
        ("pneu", "Troca de Pneus"),
        ("oleo", "Troca de Óleo"),
        ("freio", "Sistema de Freio"),
        ("outros", "Outros"),
    ]

    carro = models.ForeignKey(
        Carro, on_delete=models.CASCADE, related_name="manutencoes",
    )
    data_manutencao = models.DateField()
    data_agendamento = models.DateTimeField(default=timezone.now)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField()
    custo = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    concluida = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
    )

    class Meta:
        db_table = "carro_manutencao"
        verbose_name = _("Manutenção")
        verbose_name_plural = _("Manutenções")
        ordering = ["-data_manutencao"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.concluida and self.carro:
            from dateutil.relativedelta import relativedelta

            self.carro.data_ultima_manutencao = self.data_manutencao
            self.carro.data_proxima_manutencao = (
                self.data_manutencao + relativedelta(months=+6)
            )
            self.carro.save(
                update_fields=["data_ultima_manutencao", "data_proxima_manutencao"],
            )

    def __str__(self):
        return (
            f"Manutenção {self.get_tipo_display()} - "
            f"{self.carro.placa} - {self.data_manutencao}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# FORM (mover para forms.py futuramente)
# ═════════════════════════════════════════════════════════════════════════════

class ManutencaoForm(forms.ModelForm):
    class Meta:
        model = Carro_manutencao
        fields = [
            "data_manutencao", "tipo", "descricao",
            "custo", "concluida", "observacoes",
        ]
        widgets = {
            "data_manutencao": forms.DateInput(attrs={"type": "date"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_data_manutencao(self):
        data_manutencao = self.cleaned_data.get("data_manutencao")
        if data_manutencao and data_manutencao < timezone.now().date():
            raise forms.ValidationError(
                _("A data da manutenção não pode ser no passado."),
            )
        return data_manutencao


    