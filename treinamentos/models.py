#Treinamentos/models.py#

import uuid
from django.core.signing import Signer
from django.utils.html import mark_safe
from django.db import models
from django.urls import reverse
from django.conf import settings # Melhor prática para referenciar o User model
from django.utils import timezone
from core.managers import FilialManager
from usuario.models import Filial
from datetime import timedelta
# Necessário para a relação genérica
from django.contrib.contenttypes.fields import GenericRelation


class TipoCurso(models.Model):
    """
    Define os tipos de cursos que podem ser oferecidos,
    com suas características como modalidade, área e validade.
    """
    MODALIDADE_CHOICES = [
        ('P', 'Presencial'),
        ('O', 'Online'),
        ('H', 'Híbrido'),
    ]

    AREA_CHOICES = [
        ('ADM', 'Administrativo'),
        ('COM', 'Comportamental'),
        ('GRA', 'Graduação'),
        ('INT', 'Integração'),
        ('LID', 'Liderança'),
        ('MOT', 'Motivacional'),
        ('OPE', 'Operacional'),
        ('PRO', 'Profissionalizante'),
        ('SAU', 'Saúde'),
        ('SEG', 'Segurança'),      
        ('TEC', 'Técnico'),
    ]

    nome = models.CharField("Nome do Curso", max_length=100, unique=True)
    modalidade = models.CharField("Modalidade", max_length=1, choices=MODALIDADE_CHOICES)
    area = models.CharField("Área de Conhecimento", max_length=3, choices=AREA_CHOICES)
    
    # CORREÇÃO: Removido null=True. Uma string vazia é o padrão para campos de texto.
    descricao_no_certificado = models.TextField(
        "Descrição (para frente do certificado)", 
        blank=True, null=True,
        help_text="Texto que descreve o conteúdo, ex: 'Curso sobre Designado de CIPA...'"
    )
    
    certificado = models.BooleanField("Emite Certificado?", default=True)
    validade_meses = models.PositiveIntegerField("Validade do Certificado (meses)", 
        default=0,
        help_text="Insira 0 se o certificado não tiver validade."
    )
    ativo = models.BooleanField("Ativo", default=True)
    data_cadastro = models.DateTimeField("Data de Cadastro", auto_now_add=True)
    data_atualizacao = models.DateTimeField("Data de Atualização", auto_now=True)
    conteudo_programatico = models.TextField(
        "Conteúdo Programático", 
        blank=True, null=True,
        help_text="Texto que descreve o conteúdo, ex: 'Curso sobre Designado de CIPA...'"
    )
    referencia_normativa = models.CharField(
        "Referência Normativa", 
        max_length=255, 
        blank=True, null=True,
        help_text="Ex: 'conforme NR-5 Portaria nº 08 de 23 de fevereiro de 1.999'"
    )
    grade_curricular = models.TextField(
        "Grade Curricular (para verso)",
        blank=True, null=True,
        help_text="Conteúdo programático detalhado que aparecerá no verso. Use quebras de linha para listar os tópicos."
    )
    
    # Removido null=True para garantir que todo curso tenha uma filial.
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT,
        related_name='tipocursos',
        verbose_name="Filial",
        null=True
    )
    
    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        db_table = 'tipocurso'
        verbose_name = "Tipo de Curso"
        verbose_name_plural = "Tipos de Cursos"
        ordering = ['nome']
        permissions = [
            ('ativar_tipocurso', 'Pode ativar/desativar tipo de curso'),
            ('relatorio_tipocurso', 'Pode gerar relatórios de tipos de curso'),
        ]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        """
        Retorna a URL para a página de detalhe deste Tipo de Curso.
        Ajuste o nome 'detalhe_tipo_curso' conforme definido em seu urls.py.
        """
        # CORREÇÃO: A URL deve ser para o detalhe do TipoCurso, não do Treinamento.
        try:
            return reverse('treinamentos:detalhe_tipo_curso', kwargs={'pk': self.pk})
        except:
             # Se a rota de detalhe não existir, redireciona para a lista para evitar erros.
            return reverse('treinamentos:lista_tipos_curso')


class Treinamento(models.Model):
    """
    Armazena informações sobre cada treinamento realizado,
    incluindo datas, status, custos e participantes.
    """
    STATUS_CHOICES = [
        ('P', 'Planejado'),
        ('A', 'Em Andamento'),
        ('C', 'Cancelado'),
        ('F', 'Finalizado'),
    ]

    nome = models.CharField("Nome do Treinamento", max_length=200)
    tipo_curso = models.ForeignKey(TipoCurso, on_delete=models.PROTECT, verbose_name="Tipo de Curso")
    data_inicio = models.DateTimeField("Data de Início")
    data_fim = models.DateTimeField("Data de Fim", null=True, blank=True)
    # O campo data_vencimento pode ser calculado com base na data_inicio e validade do curso,
    # mas mantido aqui se a regra de negócio exigir uma data customizada.
    data_vencimento = models.DateField("Data de Vencimento")
    # Corrigido: 'unique=True' foi removido, pois vários treinamentos podem ter a mesma duração.
    duracao = models.IntegerField("Duração (horas)")
    atividade = models.CharField("Atividade Relacionada", max_length=200, blank=True)
    descricao = models.TextField("Descrição Detalhada")
    # Corrigido: Alterado de CharField para uma relação com o usuário responsável.
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        related_name='treinamentos_responsavel',
        verbose_name="Responsável",
        null=True,
    )
    # Campo 'cm' mantido, mas um nome mais descritivo como 'centro_custo' é recomendado.
    cm = models.CharField("CM (Centro de Custo?)", max_length=100, blank=True)
    palestrante = models.CharField("Palestrante/Instrutor", max_length=100)
    palestrante_cargo = models.CharField(
        "Cargo do Palestrante", 
        max_length=100, 
        blank=True, null=True,
        help_text="Ex: 'Técnica de Segurança do Trabalho'"
    )
    palestrante_registro = models.CharField(
        "Registro Prof. do Palestrante", 
        max_length=50, 
        blank=True, null=True,
        help_text="Ex: 'Registro do MTE SP 0073739'"
    )
    assinaturas_solicitadas = models.BooleanField(
        "Assinaturas Solicitadas",
        default=False, 
        help_text="Marca se os links de assinatura já foram enviados."
    )
    # Campo 'hxh' mantido, mas um nome como 'horas_homem' é recomendado.
    horas_homem = models.PositiveIntegerField("HxH (Horas Homem)", null=True)
    centro_custo = models.CharField("CM (Centro de Custo)", max_length=100, blank=True)
    status = models.CharField("Status", max_length=1, choices=STATUS_CHOICES, default='P')
    local = models.CharField("Local", max_length=200)
    custo = models.DecimalField("Custo Total", max_digits=10, decimal_places=2, default=0.00)
    # Corrigido: 'unique=True' foi removido.
    participantes_previstos = models.IntegerField("Nº de Participantes Previstos")
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT,
        related_name='treinamentos',
        verbose_name="Filial",
        null=True,
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()

    
    # --- INTEGRAÇÃO COM A APP 'documentos' ---
    # Adicione esta linha ao seu modelo.
    # 'documentos.Documento' = app_label.ModelName
    
    documentos = GenericRelation(
        'documentos.Documento',
        related_query_name='documento' # <--- O argumento vai aqui
    )

    class Meta:
        db_table = 'treinamento'
        verbose_name = "Treinamento"
        verbose_name_plural = "Treinamentos"
        ordering = ['-data_inicio']
        permissions = [
            ('gerenciar_participantes', 'Pode gerenciar participantes do treinamento'),
            ('alterar_status', 'Pode alterar status do treinamento'),
            ('gerar_certificados', 'Pode gerar certificados de treinamento'),
            ("ver_relatorios", "Pode visualizar o dashboard e relatórios"),
        ]

    def __str__(self):
        return f"{self.nome} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse('treinamentos:detalhe_treinamento', kwargs={'pk': self.pk})

    @property
    def dias_para_vencer(self):
        if not self.data_vencimento:
            return float('inf')  # Retorna infinito se não houver data de vencimento
        return (self.data_vencimento - timezone.now().date()).days

class Participante(models.Model):
    """
    Representa a relação entre um Funcionário (User) e um Treinamento,
    registrando presença, notas e emissão de certificado.
    """
    treinamento = models.ForeignKey(
        Treinamento,
        on_delete=models.CASCADE,
        related_name='participantes',
        verbose_name='Treinamento'
    )
    nome = models.CharField(
        max_length=200, 
        verbose_name='Nome do funcionário'
    )
    # Usando settings.AUTH_USER_MODEL para referenciar o usuário.
    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Funcionário'
    )
    presente = models.BooleanField(
        default=False,
        verbose_name='Presença Confirmada'
    )
    nota_avaliacao = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Nota da Avaliação'
    )
    certificado_emitido = models.BooleanField(
        default=False,
        verbose_name='Certificado Emitido',
    )
    data_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Registro',
        null=True,
    )
    protocolo_validacao = models.UUIDField(
        "Protocolo de Validação",
        default=uuid.uuid4,
        editable=False,
        unique=False,
        null=True,
        db_index=True,
        help_text="ID único para validação do certificado (usado no QR Code)"
    )

    class Meta:
        db_table = 'participante'
        verbose_name = 'Participante'
        verbose_name_plural = 'Participantes'
        # MELHORADO: Usando constraints, a abordagem moderna do Django.
        constraints = [
            models.UniqueConstraint(fields=['treinamento', 'funcionario'], name='inscricao_unica_por_aluno')
        ]
        permissions = [
            ('registrar_presenca', 'Pode registrar presença de participantes'),
            ('emitir_certificado', 'Pode emitir certificado para participante'),
            ('avaliar_participante', 'Pode avaliar participante'),
        ]

    def __str__(self):
        # Acessa o nome através da relação com o funcionário.
        nome_funcionario = getattr(self.funcionario, 'nome_completo', self.funcionario.username)
        return f"{nome_funcionario} - {self.treinamento.nome}"


class GabaritoCertificado(models.Model):
    """
    Armazena o template (gabarito) base para todos os certificados.
    """
    nome = models.CharField("Nome do Gabarito", max_length=100, default="Gabarito Padrão")
    empresa_nome = models.CharField("Nome da Empresa Certificadora", max_length=255, default="CETEST MINAS ENGENHARIA E SERVIÇOS S/A")
    texto_principal = models.TextField(
        "Texto Principal do Certificado",
        default="Certificamos que <strong>{participante_nome}</strong>, portador(a) do documento {participante_documento}, participou do <strong>{nome_curso}</strong> ({conteudo_programatico}), promovido pela {empresa_nome}, {referencia_normativa}, realizado em {local} no período de {data_inicio} a {data_fim}, com carga horária total de <strong>{carga_horaria} ({carga_horaria_extenso}) horas</strong>.",
        help_text="Use os placeholders disponíveis: {participante_nome}, {participante_documento}, {empresa_nome}, {nome_curso}, {conteudo_programatico}, {referencia_normativa}, {data_inicio}, {data_fim}, {carga_horaria}, {carga_horaria_extenso}, {local}"
    )
    imagem_fundo = models.ImageField(
        "Imagem de Fundo (Opcional)", 
        upload_to='certificados/fundos/', 
        null=True, blank=True
    )
    texto_verso = models.TextField(
        "Texto do Verso",
        blank=True, null=True,
        default=(
            "<h3>CONTEÚDO PROGRAMÁTICO</h3>"
            "<div class='grade-curricular'>{grade_curricular}</div>"
            "<hr>"
            "Protocolo de Validação: <strong>{protocolo}</strong><br>"
            "Para verificar a autenticidade deste certificado, aponte a câmera do seu celular para o QR Code."
        ),
        help_text="Texto padrão do verso. Use {grade_curricular}, {protocolo} e {qr_code_tag} (o QR Code será inserido aqui)."
    )
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Gabarito de Certificado"
        verbose_name_plural = "Gabaritos de Certificado"

    def __str__(self):
        return self.nome

    def renderizar_texto(self, context_dict):
        """
        Substitui os placeholders no texto principal com dados reais.
        """
        return mark_safe(self.texto_principal.format(**context_dict))
    
    def renderizar_verso(self, context_dict):
        """
        Substitui os placeholders no texto do verso com dados reais.
        """
        return mark_safe(self.texto_verso.format(**context_dict))


class Assinatura(models.Model):
    """
    Armazena a coleta de assinatura digital para um participante ou instrutor.
    """
    # Relação: Ou pertence a um participante OU ao responsável de um treinamento
    participante = models.OneToOneField(
        Participante, 
        on_delete=models.CASCADE, 
        related_name='assinatura', 
        null=True, blank=True
    )
    treinamento_responsavel = models.OneToOneField(
        Treinamento, 
        on_delete=models.CASCADE, 
        related_name='assinatura_responsavel',
        null=True, blank=True,
        help_text="Assinatura do Responsável/Instrutor pelo treinamento"
    )
    
    token_acesso = models.CharField(
        "Token de Acesso",
        max_length=100, 
        unique=True, 
        db_index=True,
        default=uuid.uuid4
    )
    assinatura_json = models.TextField("Dados da Assinatura (JSON)", blank=True, null=True)
    data_assinatura = models.DateTimeField("Data da Assinatura", null=True, blank=True)
    
    # Campos para identificar quem assinou (cache)
    nome_assinante = models.CharField(max_length=255, blank=True)
    documento_assinante = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Assinatura de Certificado"
        verbose_name_plural = "Assinaturas de Certificado"

    def __str__(self):
        if self.participante:
            return f"Assinatura de {self.participante.funcionario.get_full_name()}"
        if self.treinamento_responsavel:
            return f"Assinatura do Responsável por {self.treinamento_responsavel.nome}"
        return f"Assinatura Pendente ({self.token_acesso})"

    @property
    def esta_assinada(self):
        return self.data_assinatura is not None

    def get_signer(self):
        """ Retorna o nome de quem deve assinar. """
        if self.nome_assinante:
            return self.nome_assinante
        if self.participante:
            return self.participante.funcionario.get_full_name()
        if self.treinamento_responsavel:
            return self.treinamento_responsavel.responsavel.get_full_name()
        return "Desconhecido"
    
# =============================================================================
# =============================================================================
#
#  EVOLUÇÃO DO MÓDULO — EAD (Videoaulas, Plano de Estudo, Carga Horária)
#
#  ATENÇÃO: Todo o código acima (TipoCurso, Treinamento, Participante,
#  GabaritoCertificado, Assinatura) permanece INTACTO.
#  Os novos models coexistem com os existentes.
#
# =============================================================================
# =============================================================================

from django.core.validators import (
    FileExtensionValidator, MaxValueValidator, MinValueValidator,
)
from decimal import Decimal


# =============================================================================
# CURSO EAD
# =============================================================================

class CursoEAD(models.Model):
    """
    Curso online (EAD) com videoaulas, módulos e avaliação.
    Vinculado a um TipoCurso existente para manter compatibilidade.
    """

    class Nivel(models.TextChoices):
        BASICO = "basico", "Básico"
        INTERMEDIARIO = "intermediario", "Intermediário"
        AVANCADO = "avancado", "Avançado"

    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        PUBLICADO = "publicado", "Publicado"
        ARQUIVADO = "arquivado", "Arquivado"

    # Identificação
    titulo = models.CharField("Título do Curso", max_length=200)
    slug = models.SlugField("Slug", max_length=220, unique=True)
    descricao = models.TextField("Descrição")
    descricao_curta = models.CharField(
        "Descrição Curta", max_length=300, blank=True,
        help_text="Resumo para cards e listagens.",
    )
    imagem_capa = models.ImageField(
        "Imagem de Capa",
        upload_to="treinamentos/ead/capas/",
        blank=True, null=True,
    )

    # Vínculo com sistema existente
    tipo_curso = models.ForeignKey(
        TipoCurso,
        on_delete=models.PROTECT,
        related_name="cursos_ead",
        verbose_name="Tipo de Curso",
        help_text="Vincula ao tipo de curso existente (NR, área, etc.)",
    )

    # Configurações pedagógicas
    nivel = models.CharField(
        "Nível", max_length=20,
        choices=Nivel.choices, default=Nivel.BASICO,
    )
    carga_horaria_total = models.DecimalField(
        "Carga Horária Total (horas)",
        max_digits=6, decimal_places=1,
        help_text="Carga horária mínima exigida para certificação.",
        validators=[MinValueValidator(Decimal("0.5"))],
    )
    nota_minima = models.DecimalField(
        "Nota Mínima para Aprovação",
        max_digits=4, decimal_places=1,
        default=Decimal("7.0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("10"))],
    )
    max_tentativas_avaliacao = models.PositiveIntegerField(
        "Máx. Tentativas na Avaliação",
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    percentual_minimo_assistido = models.PositiveIntegerField(
        "% Mínimo de Conteúdo Assistido",
        default=75,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Percentual mínimo de aulas concluídas para liberar a avaliação.",
    )

    # Instrutor
    instrutor_nome = models.CharField("Nome do Instrutor", max_length=150, blank=True)
    instrutor_qualificacao = models.CharField(
        "Qualificação do Instrutor", max_length=300, blank=True,
    )

    # Status e controle
    status = models.CharField(
        "Status", max_length=20,
        choices=Status.choices, default=Status.RASCUNHO,
        db_index=True,
    )
    destaque = models.BooleanField("Em Destaque", default=False)
    publicado_em = models.DateTimeField("Publicado em", null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    # Relacionamentos
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="cursos_ead",
        verbose_name="Filial",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cursos_ead_criados",
        verbose_name="Criado por",
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Curso EAD"
        verbose_name_plural = "Cursos EAD"
        ordering = ["-destaque", "-criado_em"]
        indexes = [
            models.Index(fields=["status", "filial"], name="idx_ead_status_filial"),
        ]

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse("treinamentos:ead_curso_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLICADO and not self.publicado_em:
            self.publicado_em = timezone.now()
        super().save(*args, **kwargs)

    @property
    def total_modulos(self):
        return self.modulos_ead.count()

    @property
    def total_aulas(self):
        return AulaEAD.objects.filter(modulo__curso=self).count()

    @property
    def total_matriculados(self):
        return self.matriculas_ead.count()

    @property
    def carga_horaria_calculada(self):
        """Soma real das durações de todas as aulas (em horas)."""
        total_min = AulaEAD.objects.filter(
            modulo__curso=self
        ).aggregate(
            total=models.Sum("duracao_estimada_min")
        )["total"] or 0
        return round(total_min / 60, 1)

    @property
    def esta_publicado(self):
        return self.status == self.Status.PUBLICADO


# =============================================================================
# MÓDULO EAD
# =============================================================================

class ModuloEAD(models.Model):
    """Divisão sequencial do curso em seções temáticas."""

    curso = models.ForeignKey(
        CursoEAD,
        on_delete=models.CASCADE,
        related_name="modulos_ead",
        verbose_name="Curso",
    )
    titulo = models.CharField("Título do Módulo", max_length=200)
    descricao = models.TextField("Descrição", blank=True)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Módulo EAD"
        verbose_name_plural = "Módulos EAD"
        ordering = ["ordem"]
        unique_together = ("curso", "ordem")

    def __str__(self):
        return f"{self.ordem}. {self.titulo}"

    @property
    def total_aulas(self):
        return self.aulas_ead.count()

    @property
    def duracao_total_min(self):
        return self.aulas_ead.aggregate(
            total=models.Sum("duracao_estimada_min")
        )["total"] or 0


# =============================================================================
# AULA EAD (Videoaula, Texto, PDF)
# =============================================================================

class AulaEAD(models.Model):
    """Conteúdo individual: vídeo, texto ou PDF."""

    class TipoConteudo(models.TextChoices):
        VIDEO_UPLOAD = "video_upload", "Vídeo (Upload)"
        VIDEO_EXTERNO = "video_externo", "Vídeo Externo (YouTube/Vimeo)"
        TEXTO = "texto", "Texto/Artigo"
        PDF = "pdf", "Documento PDF"

    modulo = models.ForeignKey(
        ModuloEAD,
        on_delete=models.CASCADE,
        related_name="aulas_ead",
        verbose_name="Módulo",
    )
    titulo = models.CharField("Título da Aula", max_length=200)
    descricao = models.TextField("Descrição", blank=True)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    tipo_conteudo = models.CharField(
        "Tipo de Conteúdo",
        max_length=20,
        choices=TipoConteudo.choices,
        default=TipoConteudo.VIDEO_EXTERNO,
    )

    # === Conteúdo (dependendo do tipo) ===
    conteudo_texto = models.TextField("Conteúdo em Texto/HTML", blank=True)
    arquivo_video = models.FileField(
        "Arquivo de Vídeo",
        upload_to="treinamentos/ead/videos/",
        blank=True, null=True,
        validators=[FileExtensionValidator(["mp4", "webm", "ogg"])],
        help_text="Formatos aceitos: MP4, WebM, OGG. Máx recomendado: 500MB.",
    )
    url_video_externo = models.URLField(
        "URL do Vídeo Externo",
        blank=True,
        help_text="Cole a URL do YouTube ou Vimeo.",
    )
    arquivo_pdf = models.FileField(
        "Arquivo PDF",
        upload_to="treinamentos/ead/pdfs/",
        blank=True, null=True,
        validators=[FileExtensionValidator(["pdf"])],
    )

    # Duração e controle
    duracao_estimada_min = models.PositiveIntegerField(
        "Duração Estimada (minutos)",
        default=10,
        validators=[MinValueValidator(1)],
        help_text="Tempo estimado para completar esta aula.",
    )
    obrigatoria = models.BooleanField("Obrigatória", default=True)
    ativo = models.BooleanField("Ativa", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aula EAD"
        verbose_name_plural = "Aulas EAD"
        ordering = ["ordem"]
        unique_together = ("modulo", "ordem")

    def __str__(self):
        return f"{self.modulo.ordem}.{self.ordem} — {self.titulo}"

    @property
    def curso(self):
        return self.modulo.curso

    @property
    def embed_url(self):
        """Converte URL do YouTube/Vimeo para embed."""
        url = self.url_video_externo
        if not url:
            return ""
        # YouTube
        if "youtube.com/watch" in url:
            video_id = url.split("v=")[1].split("&")[0]
            return f"https://www.youtube.com/embed/{video_id}?rel=0"
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
            return f"https://www.youtube.com/embed/{video_id}?rel=0"
        # Vimeo
        if "vimeo.com/" in url:
            video_id = url.split("vimeo.com/")[1].split("?")[0]
            return f"https://player.vimeo.com/video/{video_id}"
        return url

    @property
    def is_video(self):
        return self.tipo_conteudo in (
            self.TipoConteudo.VIDEO_UPLOAD,
            self.TipoConteudo.VIDEO_EXTERNO,
        )


# =============================================================================
# PLANO DE ESTUDO
# =============================================================================

class PlanoEstudo(models.Model):
    """
    Trilha de aprendizado obrigatória por cargo/departamento.
    Agrupa vários CursoEAD em uma sequência com prazo.
    """

    nome = models.CharField("Nome do Plano", max_length=200)
    descricao = models.TextField("Descrição", blank=True)

    # A quem se aplica (M2M)
    cargos = models.ManyToManyField(
        "departamento_pessoal.Cargo",
        blank=True,
        related_name="planos_estudo",
        verbose_name="Cargos Aplicáveis",
    )
    departamentos = models.ManyToManyField(
        "departamento_pessoal.Departamento",
        blank=True,
        related_name="planos_estudo",
        verbose_name="Departamentos Aplicáveis",
    )

    # Cursos do plano (M2M com tabela intermediária)
    cursos = models.ManyToManyField(
        CursoEAD,
        through="PlanoEstudoCurso",
        related_name="planos_estudo",
        verbose_name="Cursos",
    )

    # Configurações
    prazo_conclusao_dias = models.PositiveIntegerField(
        "Prazo para Conclusão (dias)",
        default=30,
        help_text="Dias após matrícula para concluir todos os cursos.",
    )
    obrigatorio = models.BooleanField("Obrigatório", default=True)
    ativo = models.BooleanField("Ativo", default=True)

    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="planos_estudo",
        verbose_name="Filial",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Criado por",
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Plano de Estudo"
        verbose_name_plural = "Planos de Estudo"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse("treinamentos:plano_detail", kwargs={"pk": self.pk})

    @property
    def total_cursos(self):
        return self.plano_cursos.count()

    @property
    def carga_horaria_total(self):
        return sum(
            pc.curso.carga_horaria_total
            for pc in self.plano_cursos.select_related("curso")
        )


class PlanoEstudoCurso(models.Model):
    """Tabela intermediária: Plano ↔ CursoEAD com ordem."""

    plano = models.ForeignKey(
        PlanoEstudo,
        on_delete=models.CASCADE,
        related_name="plano_cursos",
    )
    curso = models.ForeignKey(
        CursoEAD,
        on_delete=models.CASCADE,
        related_name="plano_cursos",
    )
    ordem = models.PositiveIntegerField("Ordem", default=0)
    obrigatorio = models.BooleanField("Obrigatório", default=True)

    class Meta:
        verbose_name = "Curso do Plano"
        verbose_name_plural = "Cursos do Plano"
        ordering = ["ordem"]
        unique_together = ("plano", "curso")

    def __str__(self):
        return f"{self.plano.nome} → {self.curso.titulo}"


# =============================================================================
# MATRÍCULA EAD
# =============================================================================

class MatriculaEAD(models.Model):
    """Inscrição de um funcionário em um curso EAD."""

    class Status(models.TextChoices):
        EM_ANDAMENTO = "em_andamento", "Em Andamento"
        CONCLUIDO = "concluido", "Concluído"
        APROVADO = "aprovado", "Aprovado"
        REPROVADO = "reprovado", "Reprovado"
        CANCELADO = "cancelado", "Cancelado"
        EXPIRADO = "expirado", "Expirado"

    funcionario = models.ForeignKey(
        "departamento_pessoal.Funcionario",
        on_delete=models.PROTECT,
        related_name="matriculas_ead",
        verbose_name="Funcionário",
    )
    curso = models.ForeignKey(
        CursoEAD,
        on_delete=models.PROTECT,
        related_name="matriculas_ead",
        verbose_name="Curso EAD",
    )
    plano_estudo = models.ForeignKey(
        PlanoEstudo,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="matriculas_ead",
        verbose_name="Plano de Estudo (origem)",
    )

    # Progresso
    status = models.CharField(
        "Status", max_length=20,
        choices=Status.choices, default=Status.EM_ANDAMENTO,
        db_index=True,
    )
    progresso_percentual = models.DecimalField(
        "Progresso (%)",
        max_digits=5, decimal_places=2,
        default=Decimal("0.00"),
    )

    # ═══════════════════════════════════════════════════
    # CONTROLE DE CARGA HORÁRIA (Etapa 4)
    # ═══════════════════════════════════════════════════
    carga_horaria_cumprida_segundos = models.PositiveIntegerField(
        "Carga Horária Cumprida (segundos)",
        default=0,
        help_text="Total de segundos efetivamente gastos em aulas.",
    )

    # Notas
    nota_final = models.DecimalField(
        "Nota Final",
        max_digits=4, decimal_places=1,
        null=True, blank=True,
    )
    tentativas_avaliacao = models.PositiveIntegerField(
        "Tentativas Realizadas", default=0,
    )

    # Datas
    data_matricula = models.DateTimeField("Data da Matrícula", auto_now_add=True)
    data_conclusao = models.DateTimeField("Data de Conclusão", null=True, blank=True)
    prazo_limite = models.DateTimeField("Prazo Limite", null=True, blank=True)

    # Controle
    matriculado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Matriculado por",
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="matriculas_ead",
        verbose_name="Filial",
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Matrícula EAD"
        verbose_name_plural = "Matrículas EAD"
        ordering = ["-data_matricula"]
        constraints = [
            models.UniqueConstraint(
                fields=["funcionario", "curso"],
                name="matricula_ead_unica",
            )
        ]
        indexes = [
            models.Index(fields=["status", "filial"], name="idx_matead_status_filial"),
        ]

    def __str__(self):
        return f"{self.funcionario} → {self.curso.titulo}"

    # === Properties de carga horária ===

    @property
    def carga_horaria_cumprida_horas(self):
        """Converte segundos para horas (decimal)."""
        return Decimal(str(round(self.carga_horaria_cumprida_segundos / 3600, 1)))

    @property
    def carga_horaria_cumprida_formatada(self):
        """Ex: '6h 30min'."""
        total = self.carga_horaria_cumprida_segundos
        h = total // 3600
        m = (total % 3600) // 60
        if h > 0:
            return f"{h}h {m}min"
        return f"{m}min"

    @property
    def carga_horaria_atingida(self):
        """Verifica se cumpriu a carga horária mínima exigida."""
        return self.carga_horaria_cumprida_horas >= self.curso.carga_horaria_total

    @property
    def percentual_carga_horaria(self):
        """Percentual da CH cumprida em relação à total."""
        total = self.curso.carga_horaria_total
        if total <= 0:
            return Decimal("100.0")
        return min(
            Decimal("100.0"),
            round((self.carga_horaria_cumprida_horas / total) * 100, 1),
        )

    # === Properties de status ===

    @property
    def esta_no_prazo(self):
        if not self.prazo_limite:
            return True
        return timezone.now() <= self.prazo_limite

    @property
    def dias_restantes(self):
        if not self.prazo_limite:
            return None
        delta = self.prazo_limite - timezone.now()
        return max(delta.days, 0)

    @property
    def pode_fazer_avaliacao(self):
        """Verifica se pode liberar a avaliação."""
        return (
            self.progresso_percentual >= Decimal(str(self.curso.percentual_minimo_assistido))
            and self.tentativas_avaliacao < self.curso.max_tentativas_avaliacao
            and self.status not in (self.Status.APROVADO, self.Status.CANCELADO)
        )

    @property
    def pode_emitir_certificado(self):
        """
        REGRA DE NEGÓCIO PRINCIPAL para emissão de certificado:
        1. Aprovado na avaliação
        2. Carga horária mínima cumprida
        3. Nota >= nota mínima
        """
        return (
            self.status == self.Status.APROVADO
            and self.carga_horaria_atingida
            and self.nota_final is not None
            and self.nota_final >= self.curso.nota_minima
        )

    # === Métodos de recálculo ===

    def recalcular_progresso(self):
        """Recalcula progresso e CH com base nos ProgressoAulaEAD."""
        total_obrigatorias = AulaEAD.objects.filter(
            modulo__curso=self.curso, obrigatoria=True, ativo=True,
        ).count()

        if total_obrigatorias == 0:
            self.progresso_percentual = Decimal("100.00")
        else:
            concluidas = self.progressos_ead.filter(
                concluida=True, aula__obrigatoria=True,
            ).count()
            self.progresso_percentual = Decimal(
                str(round((concluidas / total_obrigatorias) * 100, 2))
            )

        # Recalcula carga horária total (soma de todos os tempos)
        total_seg = self.progressos_ead.aggregate(
            total=models.Sum("tempo_gasto_segundos")
        )["total"] or 0
        self.carga_horaria_cumprida_segundos = total_seg

        self.save(update_fields=[
            "progresso_percentual",
            "carga_horaria_cumprida_segundos",
        ])


# =============================================================================
# PROGRESSO POR AULA (Tracking de vídeo)
# =============================================================================

class ProgressoAulaEAD(models.Model):
    """
    Tracking individual de cada aula por aluno.
    Controla: tempo gasto, posição do vídeo, % assistido, conclusão.
    """

    matricula = models.ForeignKey(
        MatriculaEAD,
        on_delete=models.CASCADE,
        related_name="progressos_ead",
        verbose_name="Matrícula",
    )
    aula = models.ForeignKey(
        AulaEAD,
        on_delete=models.CASCADE,
        related_name="progressos_ead",
        verbose_name="Aula",
    )

    # Progresso
    concluida = models.BooleanField("Concluída", default=False)
    percentual_assistido = models.DecimalField(
        "% Assistido/Lido",
        max_digits=5, decimal_places=2,
        default=Decimal("0.00"),
    )
    tempo_gasto_segundos = models.PositiveIntegerField(
        "Tempo Gasto (segundos)", default=0,
    )

    # Para vídeos — posição de onde parou
    video_posicao_segundos = models.PositiveIntegerField(
        "Posição do Vídeo (segundos)", default=0,
        help_text="Marca de onde o aluno parou no vídeo.",
    )
    video_duracao_total = models.PositiveIntegerField(
        "Duração Total do Vídeo (segundos)", default=0,
        help_text="Preenchido automaticamente pelo player.",
    )

    # Datas
    iniciado_em = models.DateTimeField("Iniciado em", null=True, blank=True)
    concluido_em = models.DateTimeField("Concluído em", null=True, blank=True)
    ultimo_acesso = models.DateTimeField("Último Acesso", auto_now=True)

    class Meta:
        verbose_name = "Progresso da Aula EAD"
        verbose_name_plural = "Progressos das Aulas EAD"
        unique_together = ("matricula", "aula")
        ordering = ["aula__modulo__ordem", "aula__ordem"]

    def __str__(self):
        status = "✅" if self.concluida else f"{self.percentual_assistido}%"
        return f"{self.matricula.funcionario} — {self.aula.titulo} [{status}]"

    @property
    def tempo_gasto_formatado(self):
        h = self.tempo_gasto_segundos // 3600
        m = (self.tempo_gasto_segundos % 3600) // 60
        if h > 0:
            return f"{h}h {m}min"
        return f"{m}min"

    def marcar_concluida(self):
        """Marca a aula como concluída e recalcula progresso do curso."""
        if not self.concluida:
            self.concluida = True
            self.percentual_assistido = Decimal("100.00")
            self.concluido_em = timezone.now()
            self.save(update_fields=[
                "concluida", "percentual_assistido", "concluido_em",
            ])
            # Recalcula progresso geral e carga horária
            self.matricula.recalcular_progresso()


# =============================================================================
# AVALIAÇÃO ONLINE
# =============================================================================

class AvaliacaoEAD(models.Model):
    """Prova vinculada a um curso EAD."""

    curso = models.OneToOneField(
        CursoEAD,
        on_delete=models.CASCADE,
        related_name="avaliacao_ead",
        verbose_name="Curso",
    )
    titulo = models.CharField("Título", max_length=200)
    descricao = models.TextField("Instruções para o Aluno", blank=True)
    tempo_limite_min = models.PositiveIntegerField(
        "Tempo Limite (minutos)",
        default=60,
        help_text="0 = sem limite.",
    )
    embaralhar_questoes = models.BooleanField("Embaralhar Questões", default=True)
    embaralhar_alternativas = models.BooleanField("Embaralhar Alternativas", default=True)
    ativo = models.BooleanField("Ativa", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Avaliação EAD"
        verbose_name_plural = "Avaliações EAD"

    def __str__(self):
        return f"Avaliação: {self.curso.titulo}"

    @property
    def total_questoes(self):
        return self.questoes_ead.count()


class QuestaoEAD(models.Model):
    """Questão de múltipla escolha."""

    avaliacao = models.ForeignKey(
        AvaliacaoEAD,
        on_delete=models.CASCADE,
        related_name="questoes_ead",
        verbose_name="Avaliação",
    )
    enunciado = models.TextField("Enunciado")
    ordem = models.PositiveIntegerField("Ordem", default=0)
    peso = models.DecimalField(
        "Peso", max_digits=4, decimal_places=1, default=Decimal("1.0"),
    )
    explicacao = models.TextField(
        "Explicação da Resposta Correta",
        blank=True,
        help_text="Exibida após o aluno responder (feedback pedagógico).",
    )
    ativo = models.BooleanField("Ativa", default=True)

    class Meta:
        verbose_name = "Questão EAD"
        verbose_name_plural = "Questões EAD"
        ordering = ["ordem"]

    def __str__(self):
        return f"Q{self.ordem}: {self.enunciado[:80]}"


class AlternativaEAD(models.Model):
    """Opção de resposta para uma questão."""

    questao = models.ForeignKey(
        QuestaoEAD,
        on_delete=models.CASCADE,
        related_name="alternativas_ead",
        verbose_name="Questão",
    )
    texto = models.CharField("Texto da Alternativa", max_length=500)
    correta = models.BooleanField("Correta", default=False)
    ordem = models.PositiveIntegerField("Ordem", default=0)

    class Meta:
        verbose_name = "Alternativa EAD"
        verbose_name_plural = "Alternativas EAD"
        ordering = ["ordem"]

    def __str__(self):
        marca = "✔" if self.correta else "✘"
        return f"[{marca}] {self.texto[:60]}"


class TentativaAvaliacaoEAD(models.Model):
    """Cada tentativa do aluno na avaliação."""

    matricula = models.ForeignKey(
        MatriculaEAD,
        on_delete=models.CASCADE,
        related_name="tentativas_ead",
        verbose_name="Matrícula",
    )
    avaliacao = models.ForeignKey(
        AvaliacaoEAD,
        on_delete=models.CASCADE,
        related_name="tentativas_ead",
        verbose_name="Avaliação",
    )
    numero_tentativa = models.PositiveIntegerField("Nº da Tentativa", default=1)
    nota = models.DecimalField(
        "Nota Obtida", max_digits=4, decimal_places=1,
        null=True, blank=True,
    )
    aprovado = models.BooleanField("Aprovado", null=True)

    iniciada_em = models.DateTimeField("Iniciada em", auto_now_add=True)
    finalizada_em = models.DateTimeField("Finalizada em", null=True, blank=True)

    class Meta:
        verbose_name = "Tentativa de Avaliação EAD"
        verbose_name_plural = "Tentativas de Avaliação EAD"
        ordering = ["-numero_tentativa"]
        unique_together = ("matricula", "avaliacao", "numero_tentativa")

    def __str__(self):
        return f"Tentativa {self.numero_tentativa} — {self.matricula.funcionario}"

    @property
    def em_andamento(self):
        return self.finalizada_em is None

    def calcular_nota(self):
        """
        Calcula a nota e determina aprovação.
        REGRA: Aprovado = nota >= mínima E carga horária >= exigida.
        Se nota OK mas CH insuficiente → nota é salva, aprovado fica False.
        """
        respostas = self.respostas_ead.select_related(
            "questao", "alternativa_escolhida",
        )
        total_peso = sum(r.questao.peso for r in respostas)
        acertos_peso = sum(
            r.questao.peso for r in respostas
            if r.alternativa_escolhida and r.alternativa_escolhida.correta
        )

        if total_peso > 0:
            self.nota = round((acertos_peso / total_peso) * 10, 1)
        else:
            self.nota = Decimal("0.0")

        nota_suficiente = self.nota >= self.matricula.curso.nota_minima
        ch_cumprida = self.matricula.carga_horaria_atingida

        # Só aprova se AMBOS os critérios forem atendidos
        self.aprovado = nota_suficiente and ch_cumprida
        self.finalizada_em = timezone.now()
        self.save()

        # Atualiza matrícula
        matricula = self.matricula
        matricula.tentativas_avaliacao = self.numero_tentativa
        matricula.nota_final = self.nota

        if self.aprovado:
            matricula.status = MatriculaEAD.Status.APROVADO
            matricula.data_conclusao = timezone.now()
        elif (
            self.numero_tentativa >= matricula.curso.max_tentativas_avaliacao
            and not nota_suficiente
        ):
            # Só reprova definitivamente se a NOTA não foi suficiente
            # e esgotou tentativas. Se nota OK mas falta CH,
            # mantém em andamento para o aluno completar os vídeos.
            matricula.status = MatriculaEAD.Status.REPROVADO

        matricula.save()
        return self.nota


class RespostaAlunoEAD(models.Model):
    """Resposta do aluno a cada questão."""

    tentativa = models.ForeignKey(
        TentativaAvaliacaoEAD,
        on_delete=models.CASCADE,
        related_name="respostas_ead",
        verbose_name="Tentativa",
    )
    questao = models.ForeignKey(
        QuestaoEAD,
        on_delete=models.CASCADE,
        verbose_name="Questão",
    )
    alternativa_escolhida = models.ForeignKey(
        AlternativaEAD,
        on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name="Alternativa Escolhida",
    )

    class Meta:
        verbose_name = "Resposta EAD"
        verbose_name_plural = "Respostas EAD"
        unique_together = ("tentativa", "questao")

    def __str__(self):
        return f"{self.tentativa.matricula.funcionario} → Q{self.questao.ordem}"

    @property
    def esta_correta(self):
        return (
            self.alternativa_escolhida is not None
            and self.alternativa_escolhida.correta
        )


# =============================================================================
# CERTIFICADO EAD (com controle de carga horária)
# =============================================================================

class CertificadoEAD(models.Model):
    """
    Certificado emitido após aprovação + carga horária cumprida.
    Snapshot dos dados no momento da emissão para auditoria.
    """

    uuid = models.UUIDField(
        "Código de Validação",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    matricula = models.OneToOneField(
        MatriculaEAD,
        on_delete=models.PROTECT,
        related_name="certificado_ead",
        verbose_name="Matrícula",
    )

    # Snapshot (dados congelados no momento da emissão)
    nome_funcionario = models.CharField("Nome do Funcionário", max_length=255)
    cpf_funcionario = models.CharField("CPF", max_length=14, blank=True)
    nome_curso = models.CharField("Nome do Curso", max_length=200)
    nome_tipo_curso = models.CharField("Tipo de Curso", max_length=100, blank=True)
    carga_horaria_exigida = models.DecimalField(
        "CH Exigida (horas)", max_digits=6, decimal_places=1,
    )
    carga_horaria_cumprida = models.DecimalField(
        "CH Cumprida (horas)", max_digits=6, decimal_places=1,
    )
    nota = models.DecimalField("Nota Final", max_digits=4, decimal_places=1)
    nome_instrutor = models.CharField("Instrutor", max_length=150, blank=True)

    # Datas
    data_emissao = models.DateTimeField("Data de Emissão", auto_now_add=True)
    data_validade = models.DateField("Data de Validade", null=True, blank=True)

    # Arquivo PDF
    arquivo_pdf = models.FileField(
        "Arquivo PDF",
        upload_to="treinamentos/ead/certificados/",
        blank=True, null=True,
    )

    # Controle
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name="certificados_ead",
        verbose_name="Filial",
    )
    emitido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Emitido por",
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Certificado EAD"
        verbose_name_plural = "Certificados EAD"
        ordering = ["-data_emissao"]

    def __str__(self):
        return f"Certificado: {self.nome_funcionario} — {self.nome_curso}"

    def get_absolute_url(self):
        return reverse("treinamentos:certificado_ead_detail", kwargs={"uuid": self.uuid})

    @property
    def esta_valido(self):
        """Verifica se o certificado ainda está na validade."""
        if not self.data_validade:
            return True  # Sem validade = permanente
        from datetime import date
        return date.today() <= self.data_validade

    @property
    def esta_vencido(self):
        return not self.esta_valido

    def save(self, *args, **kwargs):
        # Calcula validade com base no TipoCurso
        if not self.data_validade and self.matricula:
            tipo = self.matricula.curso.tipo_curso
            if tipo.validade_meses and tipo.validade_meses > 0:
                self.data_validade = (
                    timezone.now() + timedelta(days=tipo.validade_meses * 30)
                ).date()
        super().save(*args, **kwargs)

    