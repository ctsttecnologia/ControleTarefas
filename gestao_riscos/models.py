
"""
Models do módulo de Gestão de Riscos
Integrado com PGR (Programa de Gerenciamento de Riscos)
"""
# gestao_riscos/models.py
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from core.managers import FilialManager
from usuario.models import Filial
from departamento_pessoal.models import Cargo, Funcionario
from django.utils.translation import gettext_lazy as _
from seguranca_trabalho.models import Equipamento, EntregaEPI

User = get_user_model()


# ===========================================
# CHOICES GLOBAIS
# ===========================================

CATEGORIA_RISCO_CHOICES = [
    ('fisico', 'Físico'),
    ('quimico', 'Químico'),
    ('biologico', 'Biológico'),
    ('ergonomico', 'Ergonômico'),
    ('acidente', 'Acidente/Mecânico'),
]

SETORES_CHOICES = [
    ('OPERACAO', 'Operação'),
    ('LOGISTICA', 'Logística'),
    ('MANUTENCAO', 'Manutenção'),
    ('ADMINISTRACAO', 'Administração'),
]

TIPO_OCORRENCIA_CHOICES = [
    ('', '── Selecione ──'),
    ('Incidentes', (
        ('QUASE_ACIDENTE', 'Quase Acidente (Incidente)'),
        ('CONDICAO_INSEGURA', 'Condição Insegura'),
    )),
    ('Acidentes', (
        ('ACIDENTE_SEM_AFASTAMENTO', 'Acidente sem Afastamento'),
        ('ACIDENTE_COM_AFASTAMENTO', 'Acidente com Afastamento'),
        ('ACIDENTE_TRAJETO', 'Acidente de Trajeto'),
        ('ACIDENTE_FATAL', 'Acidente Fatal'),
    )),
]

TIPO_OCORRENCIA_FLAT = [
    ('QUASE_ACIDENTE', 'Quase Acidente (Incidente)'),
    ('CONDICAO_INSEGURA', 'Condição Insegura'),
    ('ACIDENTE_SEM_AFASTAMENTO', 'Acidente sem Afastamento'),
    ('ACIDENTE_COM_AFASTAMENTO', 'Acidente com Afastamento'),
    ('ACIDENTE_TRAJETO', 'Acidente de Trajeto'),
    ('ACIDENTE_FATAL', 'Acidente Fatal'),
]

GRAVIDADE_CHOICES = [
    ('LEVE', 'Leve'),
    ('MODERADA', 'Moderada'),
    ('GRAVE', 'Grave'),
    ('GRAVISSIMA', 'Gravíssima'),
]

STATUS_CHOICES = [
    ('PENDENTE_APROVACAO', _('Pendente de Aprovação')),
    ('PENDENTE', _('Pendente')),
    ('CONCLUIDA', _('Concluída')),
    ('CANCELADA', _('Cancelada')),
]


# ===========================================
# INCIDENTE / ACIDENTE
# ===========================================

class Incidente(models.Model):
    """Registra qualquer ocorrência: incidentes E acidentes de segurança."""

    # ── Classificação ──
    classificacao = models.CharField(
        max_length=30,
        choices=TIPO_OCORRENCIA_CHOICES,
        verbose_name="Classificacao",
        default='Quase Acidente',
    )
    tipo_ocorrencia = models.CharField(
        max_length=30,
        choices=TIPO_OCORRENCIA_FLAT,
        verbose_name="Tipo de Ocorrência",
        default='Quase Acidente',
    )
    gravidade = models.CharField(
        max_length=15,
        choices=GRAVIDADE_CHOICES,
        default='LEVE',
        verbose_name="Gravidade",
    )

    # ── Descrição ──
    descricao = models.CharField(
        max_length=255,
        verbose_name="Título da Ocorrência",
    )
    detalhes = models.TextField(
        verbose_name="Detalhes da Ocorrência",
    )

    # ── Local e Data ──
    setor = models.CharField(
        max_length=20,
        choices=SETORES_CHOICES,
        verbose_name="Setor",
    )
    local_especifico = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Local Específico",
        help_text="Ex: Linha de produção 3, Pátio de carga, Escritório 2º andar",
    )
    data_ocorrencia = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data e Hora da Ocorrência",
    )

    # ── Envolvidos (Acidente) ──
    funcionario_envolvido = models.ForeignKey(
        'departamento_pessoal.Funcionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ocorrencias',
        verbose_name="Funcionário Envolvido",
        help_text="Obrigatório para acidentes",
    )
    parte_corpo_atingida = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Parte do Corpo Atingida",
        help_text="Ex: Mão direita, Coluna lombar, Olho esquerdo",
    )
    dias_afastamento = models.PositiveIntegerField(
        default=0,
        verbose_name="Dias de Afastamento",
    )
    cat_emitida = models.BooleanField(
        default=False,
        verbose_name="CAT Emitida?",
        help_text="Comunicação de Acidente de Trabalho",
    )
    numero_cat = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Nº da CAT",
    )

    # ── Ação Imediata ──
    acao_imediata = models.TextField(
        blank=True,
        verbose_name="Ação Imediata Tomada",
        help_text="Descreva o que foi feito logo após a ocorrência",
    )

    # ── Metadados ──
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='incidentes_registrados',
    )
    data_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data do Registro",
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='incidentes',
        null=True,
        blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Ocorrência"
        verbose_name_plural = "Ocorrências"
        ordering = ['-data_ocorrencia']

    def __str__(self):
        return f"[{self.get_tipo_ocorrencia_display()}] {self.descricao}"

    @property
    def is_acidente(self):
        return self.tipo_ocorrencia.startswith('ACIDENTE')

    @property
    def is_incidente(self):
        return not self.is_acidente

    @property
    def cor_gravidade(self):
        cores = {
            'LEVE': 'success',
            'MODERADA': 'warning',
            'GRAVE': 'danger',
            'GRAVISSIMA': 'dark',
        }
        return cores.get(self.gravidade, 'secondary')

    @property
    def cor_tipo(self):
        if self.tipo_ocorrencia == 'ACIDENTE_FATAL':
            return 'dark'
        if self.is_acidente:
            return 'danger'
        return 'warning'


# ===========================================
# INSPEÇÃO
# ===========================================

class Inspecao(models.Model):
    """Agenda e registra inspeções de segurança."""

    equipamento = models.ForeignKey(
        'seguranca_trabalho.Equipamento',
        on_delete=models.SET_NULL,
        related_name='inspecoes',
        null=True, blank=True,
    )

    entrega_epi = models.ForeignKey(
        'seguranca_trabalho.EntregaEPI',
        on_delete=models.CASCADE,
        related_name='inspecoes',
        null=True, blank=True,
        verbose_name=_("Item de EPI Específico"),
    )

    data_agendada = models.DateField(verbose_name="Data Agendada")
    data_realizacao = models.DateField(verbose_name="Data de Realização", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')

    responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='inspecoes_realizadas',
    )
    observacoes = models.TextField(blank=True)
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='inspecoes',
        null=True, blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Inspeção"
        verbose_name_plural = "Inspeções"
        ordering = ['-data_agendada']

    def __str__(self):
        if self.entrega_epi:
            return f"Inspeção de {self.entrega_epi} em {self.data_agendada}"
        if self.equipamento:
            return f"Inspeção de {self.equipamento.nome} em {self.data_agendada}"
        return f"Inspeção (ID: {self.id}) em {self.data_agendada}"

    def save(self, *args, **kwargs):
        if self.entrega_epi:
            if not self.equipamento_id:
                self.equipamento = self.entrega_epi.equipamento
            if not self.filial_id:
                self.filial = self.entrega_epi.filial

        if not self.equipamento_id and not self.entrega_epi_id:
            raise ValueError("A inspeção deve estar ligada a um Equipamento ou a uma Entrega de EPI.")

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse_lazy('gestao_riscos:inspecao_detalhe', kwargs={'pk': self.pk})


# ===========================================
# CARTÃO TAG
# ===========================================

class CartaoTag(models.Model):
    """Representa um Cartão de Bloqueio (Tag de Perigo) individual para um funcionário."""

    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='cartoes_tag',
        verbose_name="Funcionário Proprietário",
    )
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.CASCADE,
        related_name='cartoes_tag',
        verbose_name="Cargo",
        null=True,
        blank=True,
        default=None,
    )
    fone = models.CharField(
        max_length=20,
        default="(11) 3045-9400",
        verbose_name="Telefone de Contato",
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_validade = models.DateField(verbose_name="Data de Validade", null=True, blank=True)
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='cartoes_tag',
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Cartão de Bloqueio (Tag)"
        verbose_name_plural = "Cartões de Bloqueio (Tags)"
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Cartão de {self.funcionario.nome_completo}"


# ===========================================
# RISCOS
# ===========================================

class TipoRisco(models.Model):

    CORES_CATEGORIA = {
        'fisico': '#00a651',
        'quimico': '#ed1c24',
        'biologico': '#8B4513',
        'ergonomico': '#f7ec13',
        'acidente': '#0068b7',
    }

    categoria = models.CharField(
        'Categoria',
        max_length=20,
        choices=CATEGORIA_RISCO_CHOICES,
    )
    nome = models.CharField('Nome do Risco', max_length=200)
    descricao = models.TextField('Descrição', blank=True)
    codigo_cor = models.CharField(
        'Código da Cor',
        max_length=7,
        default='#808080',
        help_text='Cor no formato hexadecimal (#RRGGBB)',
    )
    nr_referencia = models.CharField(
        'NR de Referência',
        max_length=50,
        blank=True,
        help_text='Ex: NR-15, NR-17',
    )
    ativo = models.BooleanField('Ativo', default=True)
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='tipos_risco',
    )

    objects = FilialManager()

    class Meta:
        db_table = 'gestao_tipo_risco'
        verbose_name = 'Tipo de Risco'
        verbose_name_plural = 'Tipos de Riscos'
        ordering = ['categoria', 'nome']
        unique_together = ['categoria', 'nome', 'filial']

    def __str__(self):
        return f"{self.get_categoria_display()} - {self.nome}"

    def get_cor_categoria(self):
        return self.CORES_CATEGORIA.get(self.categoria, '#808080')

    def save(self, *args, **kwargs):
        if self.codigo_cor == '#808080':
            self.codigo_cor = self.get_cor_categoria()
        super().save(*args, **kwargs)
