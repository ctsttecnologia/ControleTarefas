# departamento_pessoal/models.py

"""
Models do app Departamento Pessoal.

Representa departamentos, cargos, funcionários e seus documentos.

Arquitetura de Filial:
  ✅ Models com campo `filial` direto → FilialManager
"""

from datetime import date

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.managers import FilialManager
from core.upload import make_upload_path
from core.validators import SecureFileValidator, SecureImageValidator
from usuario.models import Filial
from cliente.models import Cliente


# ═════════════════════════════════════════════════════════════════════════════
# DEPARTAMENTO
# ═════════════════════════════════════════════════════════════════════════════

class Departamento(models.Model):
    """
    Representa um departamento dentro de uma filial da empresa.
    Ex: Financeiro, Recursos Humanos, TI.
    """

    registro = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Registro de Departamento"),
    )
    nome = models.CharField(
        _("Nome do Departamento"),
        max_length=100,
        unique=True,
    )
    centro_custo = models.CharField(
        _("Centro de Custo"),
        max_length=20,
        unique=True,
        blank=True,
        null=True,
    )
    ativo = models.BooleanField(
        _("Ativo"),
        default=True,
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="departamentos",
        verbose_name=_("Filial"),
        null=True,
        blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Departamento")
        verbose_name_plural = _("Departamentos")
        ordering = ["nome"]

    def __str__(self):
        return self.nome


# ═════════════════════════════════════════════════════════════════════════════
# CARGO
# ═════════════════════════════════════════════════════════════════════════════

class Cargo(models.Model):
    """
    Representa um cargo ou função exercida dentro da empresa.
    Ex: Analista Financeiro, Desenvolvedor Pleno.
    """

    nome = models.CharField(
        _("Nome do Cargo"),
        max_length=100,
        unique=True,
    )
    descricao = models.TextField(
        _("Descrição Sumária do Cargo"),
        blank=True,
    )
    cbo = models.CharField(
        _("CBO"),
        max_length=10,
        blank=True,
        help_text=_("Classificação Brasileira de Ocupações"),
    )
    ativo = models.BooleanField(
        _("Ativo"),
        default=True,
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="cargos",
        verbose_name=_("Filial"),
        null=True,
        blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Cargo")
        verbose_name_plural = _("Cargos")
        ordering = ["nome"]

    def __str__(self):
        return self.nome


# ═════════════════════════════════════════════════════════════════════════════
# FUNCIONÁRIO
# ═════════════════════════════════════════════════════════════════════════════

class Funcionario(models.Model):
    """
    Modelo central que representa um colaborador da empresa, unindo
    dados pessoais, de contato e de contratação.
    """

    STATUS_CHOICES = [
        ("ATIVO", _("Ativo")),
        ("INATIVO", _("Inativo")),
        ("FERIAS", _("Férias")),
        ("AFASTADO", _("Afastado")),
    ]
    SEXO_CHOICES = [
        ("M", _("Masculino")),
        ("F", _("Feminino")),
        ("O", _("Outro")),
    ]

    # ── Relacionamentos ──────────────────────────────────────────────────────
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="funcionario",
        verbose_name=_("Usuário do Sistema"),
        null=True,
        blank=True,
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="funcionarios",
        verbose_name=_("Filial"),
        null=True,
        blank=True,
    )
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.PROTECT,
        related_name="funcionarios",
        verbose_name=_("Cargo"),
    )
    funcao = models.ForeignKey(
        "seguranca_trabalho.Funcao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Função (SST)"),
        help_text=_("Função desempenhada pelo funcionário para fins de SST e Matriz de EPI."),
        related_name="funcionarios_dp",
        related_query_name="funcionario_dp",
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name="funcionarios",
        verbose_name=_("Departamento"),
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        related_name="funcionarios_alocados",
        verbose_name=_("Cliente/Contrato"),
        null=True,
        blank=True,
    )

    # ── Informações Pessoais ─────────────────────────────────────────────────
    nome_completo = models.CharField(_("Nome Completo"), max_length=255)
    data_nascimento = models.DateField(_("Data de Nascimento"), null=True, blank=True)
    sexo = models.CharField(
        _("Sexo"),
        max_length=1,
        choices=SEXO_CHOICES,
        null=True,
        blank=True,
    )
    email_pessoal = models.EmailField(
        _("Email Pessoal"),
        unique=True,
        null=True,
        blank=True,
    )
    telefone = models.CharField(
        _("Telefone de Contato"),
        max_length=20,
        blank=True,
    )

    # ── Informações de Contratação ───────────────────────────────────────────
    matricula = models.CharField(_("Matrícula"), max_length=20, unique=True)
    data_admissao = models.DateField(_("Data de Admissão"))
    data_demissao = models.DateField(_("Data de Demissão"), null=True, blank=True)
    salario = models.DecimalField(
        _("Salário Base"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
    )
    status = models.CharField(
        _("Status"),
        max_length=10,
        choices=STATUS_CHOICES,
        default="ATIVO",
    )

    # ── Upload — Foto 3x4 ───────────────────────────────────────────────────
    foto_3x4 = models.ImageField(
        _("Foto 3x4"),
        upload_to=make_upload_path("departamento_pessoal_foto"),
        validators=[SecureImageValidator("departamento_pessoal_foto")],
        null=True,
        blank=True,
        help_text=_("Imagem JPG, PNG ou WebP (máx. 4 MB)."),
    )

    # ── Metadados ────────────────────────────────────────────────────────────
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = FilialManager()

    class Meta:
        verbose_name = _("Funcionário")
        verbose_name_plural = _("Funcionários")
        ordering = ["nome_completo"]

    def __str__(self):
        return self.nome_completo

    def get_absolute_url(self):
        return reverse("departamento_pessoal:detalhe_funcionario", kwargs={"pk": self.pk})

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        """
        Sanitiza imagem da foto 3x4 e remove arquivo antigo se substituído.
        """
        from core.upload import sanitize_image, delete_old_file

        # Remove arquivo antigo ao substituir
        if self.pk:
            delete_old_file(self, "foto_3x4")

        super().save(*args, **kwargs)

        # Sanitiza a imagem salva (strip EXIF, recodifica)
        if self.foto_3x4:
            sanitize_image(self.foto_3x4.path)

    def delete(self, *args, **kwargs):
        """Remove arquivo físico ao excluir o registro."""
        from core.upload import safe_delete_file

        safe_delete_file(self, "foto_3x4")
        super().delete(*args, **kwargs)

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def idade(self):
        """Calcula a idade do funcionário com base na data de nascimento."""
        if not self.data_nascimento:
            return None
        hoje = date.today()
        return (
            hoje.year
            - self.data_nascimento.year
            - ((hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day))
        )

    @property
    def rg_numero(self):
        """Retorna o número do RG do funcionário, se existir."""
        try:
            return self.documentos_dp.get(tipo_documento="RG").numero
        except Documento.DoesNotExist:
            return "N/A"


# ═════════════════════════════════════════════════════════════════════════════
# DOCUMENTO
# ═════════════════════════════════════════════════════════════════════════════

class Documento(models.Model):
    """
    Armazena documentos pessoais e profissionais de funcionários.
    Campos específicos são exibidos condicionalmente conforme o tipo.
    """

    # ── Tipos de documento ───────────────────────────────────────────────────
    TIPO_CHOICES = [
        # Documentos pessoais
        ("CPF", "CPF"),
        ("RG", "RG / Carteira de Identidade"),
        ("CNH", "CNH - Carteira de Habilitação"),
        ("CTPS", "CTPS - Carteira de Trabalho"),
        ("PIS", "PIS / PASEP / NIT"),
        ("TITULO", "Título de Eleitor"),
        ("RESERVISTA", "Certificado de Reservista"),
        ("CERTIDAO_NASC", "Certidão de Nascimento"),
        ("CERTIDAO_CAS", "Certidão de Casamento"),
        ("PASSAPORTE", "Passaporte"),
        ("RNE", "RNE / CRNM (Estrangeiro)"),
        # Documentos profissionais
        ("REGISTRO_CLASSE", "Registro de Classe (CREA, CRM, OAB, etc.)"),
        ("CERTIFICADO", "Certificado / Diploma"),
        ("ASO", "ASO - Atestado de Saúde Ocupacional"),
        ("NR", "Certificado de NR (NR-10, NR-35, etc.)"),
        ("COMPROVANTE_END", "Comprovante de Endereço"),
        ("COMP_ESCOLAR", "Comprovante de Escolaridade"),
        ("OUTRO", "Outro"),
    ]

    # ── Categorias de CNH ────────────────────────────────────────────────────
    CNH_CATEGORIA_CHOICES = [
        ("A", "A - Motos"),
        ("B", "B - Carros"),
        ("AB", "AB - Motos e Carros"),
        ("C", "C - Caminhões"),
        ("D", "D - Ônibus"),
        ("E", "E - Carretas / Articulados"),
        ("AC", "AC"),
        ("AD", "AD"),
        ("AE", "AE"),
    ]

    # ── UF para órgão expedidor ──────────────────────────────────────────────
    UF_CHOICES = [
        ("AC", "AC"), ("AL", "AL"), ("AM", "AM"), ("AP", "AP"),
        ("BA", "BA"), ("CE", "CE"), ("DF", "DF"), ("ES", "ES"),
        ("GO", "GO"), ("MA", "MA"), ("MG", "MG"), ("MS", "MS"),
        ("MT", "MT"), ("PA", "PA"), ("PB", "PB"), ("PE", "PE"),
        ("PI", "PI"), ("PR", "PR"), ("RJ", "RJ"), ("RN", "RN"),
        ("RO", "RO"), ("RR", "RR"), ("RS", "RS"), ("SC", "SC"),
        ("SE", "SE"), ("SP", "SP"), ("TO", "TO"),
    ]

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS COMUNS A TODOS OS TIPOS
    # ═════════════════════════════════════════════════════════════════════════

    funcionario = models.ForeignKey(
        "departamento_pessoal.Funcionario",
        on_delete=models.PROTECT,
        verbose_name=_("Funcionário"),
        related_name="documentos_dp",
        related_query_name="documento_dp",
    )
    tipo_documento = models.CharField(
        _("Tipo de Documento"),
        max_length=20,
        choices=TIPO_CHOICES,
    )
    numero = models.CharField(
        _("Número do Documento"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Número principal do documento"),
    )
    data_emissao = models.DateField(
        _("Data de Emissão"),
        blank=True,
        null=True,
    )
    data_validade = models.DateField(
        _("Data de Validade"),
        blank=True,
        null=True,
        help_text=_("Deixe em branco se não tem validade"),
    )
    orgao_expedidor = models.CharField(
        _("Órgão Expedidor"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Ex: SSP-MG, DETRAN-SP, CREA-MG"),
    )
    uf_expedidor = models.CharField(
        _("UF do Expedidor"),
        max_length=2,
        choices=UF_CHOICES,
        blank=True,
        null=True,
    )
    observacoes = models.TextField(
        _("Observações"),
        blank=True,
        null=True,
    )

    # ── Upload — Anexo ───────────────────────────────────────────────────────
    anexo = models.FileField(
        _("Arquivo Anexado"),
        upload_to=make_upload_path("departamento_pessoal"),
        validators=[SecureFileValidator("departamento_pessoal")],
        blank=True,
        null=True,
        help_text=_("PDF ou imagem (máx. 10 MB)."),
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — RG
    # ═════════════════════════════════════════════════════════════════════════

    rg_nome_pai = models.CharField(
        _("Nome do Pai"), max_length=200, blank=True, null=True,
    )
    rg_nome_mae = models.CharField(
        _("Nome da Mãe"), max_length=200, blank=True, null=True,
    )
    rg_naturalidade = models.CharField(
        _("Naturalidade"), max_length=100, blank=True, null=True,
        help_text=_("Ex: Belo Horizonte/MG"),
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — CNH
    # ═════════════════════════════════════════════════════════════════════════

    cnh_categoria = models.CharField(
        _("Categoria da CNH"), max_length=3,
        choices=CNH_CATEGORIA_CHOICES, blank=True, null=True,
    )
    cnh_numero_registro = models.CharField(
        _("Nº de Registro CNH"), max_length=30, blank=True, null=True,
    )
    cnh_primeira_habilitacao = models.DateField(
        _("Data da 1ª Habilitação"), blank=True, null=True,
    )
    cnh_observacoes_detran = models.CharField(
        _("Observações DETRAN"), max_length=200, blank=True, null=True,
        help_text=_("Ex: Exerce Atividade Remunerada (EAR)"),
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — CTPS
    # ═════════════════════════════════════════════════════════════════════════

    ctps_serie = models.CharField(
        _("Série da CTPS"), max_length=20, blank=True, null=True,
    )
    ctps_uf = models.CharField(
        _("UF da CTPS"), max_length=2,
        choices=UF_CHOICES, blank=True, null=True,
    )
    ctps_digital = models.BooleanField(
        _("CTPS Digital?"), default=False,
        help_text=_("Marque se a CTPS é digital (sem número físico)"),
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — TÍTULO DE ELEITOR
    # ═════════════════════════════════════════════════════════════════════════

    titulo_zona = models.CharField(
        _("Zona Eleitoral"), max_length=10, blank=True, null=True,
    )
    titulo_secao = models.CharField(
        _("Seção Eleitoral"), max_length=10, blank=True, null=True,
    )
    titulo_municipio = models.CharField(
        _("Município"), max_length=100, blank=True, null=True,
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — RESERVISTA
    # ═════════════════════════════════════════════════════════════════════════

    reservista_categoria = models.CharField(
        _("Categoria Reservista"), max_length=10, blank=True, null=True,
    )
    reservista_regiao_militar = models.CharField(
        _("Região Militar"), max_length=50, blank=True, null=True,
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — REGISTRO DE CLASSE
    # ═════════════════════════════════════════════════════════════════════════

    registro_orgao = models.CharField(
        _("Órgão de Classe"), max_length=50, blank=True, null=True,
        help_text=_("Ex: CREA, CRM, OAB, CRN, COREN"),
    )
    registro_especialidade = models.CharField(
        _("Especialidade"), max_length=200, blank=True, null=True,
        help_text=_("Ex: Engenharia Mecânica e de Segurança do Trabalho"),
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — ASO
    # ═════════════════════════════════════════════════════════════════════════

    ASO_TIPO_CHOICES = [
        ("admissional", "Admissional"),
        ("periodico", "Periódico"),
        ("retorno", "Retorno ao Trabalho"),
        ("mudanca", "Mudança de Função"),
        ("demissional", "Demissional"),
    ]

    aso_tipo_exame = models.CharField(
        _("Tipo de Exame ASO"), max_length=20,
        choices=ASO_TIPO_CHOICES, blank=True, null=True,
    )
    aso_apto = models.BooleanField(
        _("Apto?"), default=True, null=True,
        help_text=_("Resultado: Apto ou Inapto"),
    )
    aso_medico_nome = models.CharField(
        _("Médico Responsável"), max_length=200, blank=True, null=True,
    )
    aso_medico_crm = models.CharField(
        _("CRM do Médico"), max_length=20, blank=True, null=True,
    )
    aso_proximo_exame = models.DateField(
        _("Próximo Exame"), blank=True, null=True,
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — CERTIFICADO NR
    # ═════════════════════════════════════════════════════════════════════════

    nr_numero = models.CharField(
        _("Número da NR"), max_length=10, blank=True, null=True,
        help_text=_("Ex: NR-10, NR-35, NR-33"),
    )
    nr_carga_horaria = models.PositiveIntegerField(
        _("Carga Horária (horas)"), blank=True, null=True,
    )
    nr_instituicao = models.CharField(
        _("Instituição / Empresa"), max_length=200, blank=True, null=True,
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — CERTIFICADO / DIPLOMA
    # ═════════════════════════════════════════════════════════════════════════

    ESCOLARIDADE_CHOICES = [
        ("fundamental", "Ensino Fundamental"),
        ("medio", "Ensino Médio"),
        ("tecnico", "Curso Técnico"),
        ("graduacao", "Graduação"),
        ("pos", "Pós-Graduação / MBA"),
        ("mestrado", "Mestrado"),
        ("doutorado", "Doutorado"),
        ("curso_livre", "Curso Livre / Extensão"),
    ]

    certificado_nivel = models.CharField(
        _("Nível/Grau"), max_length=20,
        choices=ESCOLARIDADE_CHOICES, blank=True, null=True,
    )
    certificado_curso = models.CharField(
        _("Nome do Curso"), max_length=200, blank=True, null=True,
    )
    certificado_instituicao = models.CharField(
        _("Instituição de Ensino"), max_length=200, blank=True, null=True,
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — PASSAPORTE
    # ═════════════════════════════════════════════════════════════════════════

    passaporte_pais_emissao = models.CharField(
        _("País de Emissão"), max_length=100,
        blank=True, null=True, default="Brasil",
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CAMPO GENÉRICO — OUTRO
    # ═════════════════════════════════════════════════════════════════════════

    outro_descricao = models.CharField(
        _("Descrição do Documento"), max_length=200,
        blank=True, null=True,
        help_text=_('Descreva o tipo de documento quando "Outro"'),
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CONTROLE / FILIAL
    # ═════════════════════════════════════════════════════════════════════════

    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="documentos_dp_filial",
        verbose_name=_("Filial"),
        null=True,
        blank=False,
    )

    _filial_lookup = "filial_id"
    objects = FilialManager()

    criado_em = models.DateTimeField(_("Criado em"), auto_now_add=True)
    atualizado_em = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        db_table = "departamento_pessoal_documento"
        verbose_name = _("Documento")
        verbose_name_plural = _("Documentos")
        unique_together = ("funcionario", "tipo_documento", "numero")
        ordering = ["funcionario__nome_completo", "tipo_documento"]

    def __str__(self):
        return f"{self.get_tipo_documento_display()} — {self.funcionario.nome_completo}"

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        """
        Remove arquivo antigo ao substituir e sanitiza imagens anexadas.
        """
        from core.upload import delete_old_file, sanitize_image

        if self.pk:
            delete_old_file(self, "anexo")

        super().save(*args, **kwargs)

        # Se o anexo for imagem, sanitiza (strip EXIF, recodifica)
        if self.anexo and self.anexo.name:
            ext = self.anexo.name.rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "png", "webp"):
                sanitize_image(self.anexo.path)

    def delete(self, *args, **kwargs):
        """Remove arquivo físico ao excluir o registro."""
        from core.upload import safe_delete_file

        safe_delete_file(self, "anexo")
        super().delete(*args, **kwargs)


    def clean(self):
        """Validações condicionais por tipo de documento."""
        from django.core.exceptions import ValidationError

        errors = {}

        # CPF — validação de formato
        if self.tipo_documento == "CPF" and self.numero:
            cpf = self.numero.replace(".", "").replace("-", "").replace(" ", "")
            if len(cpf) != 11 or not cpf.isdigit():
                errors["numero"] = _("CPF deve ter 11 dígitos numéricos.")

        # CNH — categoria obrigatória
        if self.tipo_documento == "CNH":
            if not self.cnh_categoria:
                errors["cnh_categoria"] = _("Categoria é obrigatória para CNH.")
            if not self.data_validade:
                errors["data_validade"] = _("Data de validade é obrigatória para CNH.")

        # CTPS — série obrigatória se não digital
        if self.tipo_documento == "CTPS" and not self.ctps_digital:
            if not self.numero:
                errors["numero"] = _("Número é obrigatório para CTPS física.")
            if not self.ctps_serie:
                errors["ctps_serie"] = _("Série é obrigatória para CTPS física.")

        # ASO — tipo de exame obrigatório
        if self.tipo_documento == "ASO" and not self.aso_tipo_exame:
            errors["aso_tipo_exame"] = _("Tipo de exame é obrigatório para ASO.")

        # NR — número da NR obrigatório
        if self.tipo_documento == "NR" and not self.nr_numero:
            errors["nr_numero"] = _("Número da NR é obrigatório.")

        # OUTRO — descrição obrigatória
        if self.tipo_documento == "OUTRO" and not self.outro_descricao:
            errors["outro_descricao"] = _('Descrição é obrigatória para tipo "Outro".')

        if errors:
            raise ValidationError(errors)

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def esta_vencido(self):
        """Retorna True se o documento está vencido."""
        if self.data_validade:
            return self.data_validade < date.today()
        return False

    @property
    def vence_em_30_dias(self):
        """Retorna True se vence nos próximos 30 dias."""
        if self.data_validade:
            from datetime import timedelta

            hoje = date.today()
            return hoje <= self.data_validade <= hoje + timedelta(days=30)
        return False

    @property
    def icone(self):
        """Retorna ícone Bootstrap para o tipo de documento."""
        icones = {
            "CPF": "bi-person-vcard",
            "RG": "bi-person-badge",
            "CNH": "bi-car-front",
            "CTPS": "bi-briefcase-fill",
            "PIS": "bi-123",
            "TITULO": "bi-check2-square",
            "RESERVISTA": "bi-shield-check",
            "CERTIDAO_NASC": "bi-file-earmark-person",
            "CERTIDAO_CAS": "bi-heart",
            "PASSAPORTE": "bi-globe",
            "RNE": "bi-globe2",
            "REGISTRO_CLASSE": "bi-award",
            "CERTIFICADO": "bi-mortarboard",
            "ASO": "bi-heart-pulse",
            "NR": "bi-shield-exclamation",
            "COMPROVANTE_END": "bi-house",
            "COMP_ESCOLAR": "bi-book",
            "OUTRO": "bi-file-earmark-text",
        }
        return icones.get(self.tipo_documento, "bi-file-earmark")

    @property
    def cor_badge(self):
        """Retorna a cor do badge conforme status de validade."""
        if self.esta_vencido:
            return "danger"
        if self.vence_em_30_dias:
            return "warning"
        return "success"

