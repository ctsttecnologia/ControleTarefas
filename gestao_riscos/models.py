# =============================================================================
# gestao_riscos/mixins.py
# =============================================================================
from core.mixins import (
    AppPermissionMixin,
    FuncionarioRequiredMixin,
    RequireActiveFilialMixin,
    TecnicoScopeMixin,
    ViewFilialScopedMixin,
)


class GestaoRiscosBaseMixin(FuncionarioRequiredMixin, AppPermissionMixin):
    """Auth + vínculo Funcionário + permissão por app (ou granular, se a view definir)."""
    modulo_nome = 'Gestão de Riscos'
    app_label_required = 'gestao_riscos'


class GestaoRiscosWriteMixin(GestaoRiscosBaseMixin, RequireActiveFilialMixin):
    """Escrita: exige filial ativa. Defina `permission_required` na view."""


class GestaoRiscosTecnicoMixin(GestaoRiscosBaseMixin, TecnicoScopeMixin, ViewFilialScopedMixin):
    """CRUD com escopo de técnico + filial. Defina `tecnico_scope_lookup`."""


# =============================================================================
# gestao_riscos/models.py
# =============================================================================
from django.conf import settings
from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.managers import FilialManager
from departamento_pessoal.models import Cargo, Funcionario
from usuario.models import Filial

User = settings.AUTH_USER_MODEL

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

TIPO_OCORRENCIA_FLAT = [
    ('QUASE_ACIDENTE', 'Quase Acidente (Incidente)'),
    ('CONDICAO_INSEGURA', 'Condição Insegura'),
    ('ACIDENTE_SEM_AFASTAMENTO', 'Acidente sem Afastamento'),
    ('ACIDENTE_COM_AFASTAMENTO', 'Acidente com Afastamento'),
    ('ACIDENTE_TRAJETO', 'Acidente de Trajeto'),
    ('ACIDENTE_FATAL', 'Acidente Fatal'),
]

TIPO_OCORRENCIA_CHOICES = [
    ('', '── Selecione ──'),
    ('Incidentes', TIPO_OCORRENCIA_FLAT[:2]),
    ('Acidentes', TIPO_OCORRENCIA_FLAT[2:]),
]

# Ocorrências que "zeram" o contador de dias sem acidentes
TIPOS_ZERAM_CONTADOR = ('ACIDENTE_COM_AFASTAMENTO', 'ACIDENTE_FATAL')

CLASSIFICACAO_CHOICES = [('INCIDENTE', 'Incidente'), ('ACIDENTE', 'Acidente')]

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

hex_color_validator = RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Use o formato #RRGGBB.')


class Incidente(models.Model):
    """Ocorrência de SST. Campos de saúde são DADO SENSÍVEL (LGPD art. 11)."""

    # Derivado de tipo_ocorrencia no save() (mantido p/ relatórios/compat.)
    classificacao = models.CharField(
        max_length=30, choices=CLASSIFICACAO_CHOICES, default='INCIDENTE',
        editable=False, verbose_name='Classificação',
    )
    tipo_ocorrencia = models.CharField(
        max_length=30, choices=TIPO_OCORRENCIA_FLAT, default='QUASE_ACIDENTE',
        verbose_name='Tipo de Ocorrência', db_index=True,
    )
    gravidade = models.CharField(max_length=15, choices=GRAVIDADE_CHOICES, default='LEVE')

    descricao = models.CharField('Título da Ocorrência', max_length=255)
    detalhes = models.TextField('Detalhes da Ocorrência')

    setor = models.CharField('Setor', max_length=20, choices=SETORES_CHOICES)
    local_especifico = models.CharField('Local Específico', max_length=255, blank=True)
    data_ocorrencia = models.DateTimeField('Data e Hora da Ocorrência', default=timezone.now)

    # ── Envolvidos / dados de saúde (sensíveis) ──
    funcionario_envolvido = models.ForeignKey(
        Funcionario, on_delete=models.PROTECT,  # preserva histórico legal (NR/eSocial)
        null=True, blank=True, related_name='ocorrencias',
        verbose_name='Funcionário Envolvido',
    )
    parte_corpo_atingida = models.CharField('Parte do Corpo Atingida', max_length=255, blank=True)
    dias_afastamento = models.PositiveIntegerField('Dias de Afastamento', default=0)
    cat_emitida = models.BooleanField('CAT Emitida?', default=False)
    numero_cat = models.CharField('Nº da CAT', max_length=50, blank=True)

    acao_imediata = models.TextField('Ação Imediata Tomada', blank=True)

    registrado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='incidentes_registrados',
    )
    data_registro = models.DateTimeField('Data do Registro', auto_now_add=True)
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='incidentes')

    objects = FilialManager()

    class Meta:
        verbose_name = 'Ocorrência'
        verbose_name_plural = 'Ocorrências'
        ordering = ['-data_ocorrencia']
        indexes = [models.Index(fields=['filial', 'tipo_ocorrencia', '-data_ocorrencia'])]
        permissions = [
            ('view_all_incidente', _('Pode visualizar todas as ocorrências da filial')),
            ('view_dados_saude_incidente', _('Pode visualizar dados de saúde (LGPD)')),
        ]

    def __str__(self):
        return f"[{self.get_tipo_ocorrencia_display()}] {self.descricao}"

    def save(self, *args, **kwargs):
        self.classificacao = 'ACIDENTE' if self.is_acidente else 'INCIDENTE'
        if not self.cat_emitida:
            self.numero_cat = ''
        super().save(*args, **kwargs)

    @property
    def is_acidente(self):
        return (self.tipo_ocorrencia or '').startswith('ACIDENTE')

    @property
    def is_incidente(self):
        return not self.is_acidente

    @property
    def cor_gravidade(self):
        return {'LEVE': 'success', 'MODERADA': 'warning',
                'GRAVE': 'danger', 'GRAVISSIMA': 'dark'}.get(self.gravidade, 'secondary')

    @property
    def cor_tipo(self):
        if self.tipo_ocorrencia == 'ACIDENTE_FATAL':
            return 'dark'
        return 'danger' if self.is_acidente else 'warning'


class Inspecao(models.Model):
    equipamento = models.ForeignKey(
        'seguranca_trabalho.Equipamento', on_delete=models.SET_NULL,
        related_name='inspecoes', null=True, blank=True,
    )
    entrega_epi = models.ForeignKey(
        'seguranca_trabalho.EntregaEPI', on_delete=models.CASCADE,
        related_name='inspecoes', null=True, blank=True,
        verbose_name=_('Item de EPI Específico'),
    )
    data_agendada = models.DateField('Data Agendada')
    data_realizacao = models.DateField('Data de Realização', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    responsavel = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inspecoes_realizadas',
    )
    observacoes = models.TextField(blank=True)
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='inspecoes')

    objects = FilialManager()

    class Meta:
        verbose_name = 'Inspeção'
        verbose_name_plural = 'Inspeções'
        ordering = ['-data_agendada']
        indexes = [models.Index(fields=['filial', 'status', 'data_agendada'])]
        permissions = [
            ('view_all_inspecao', _('Pode visualizar todas as inspeções da filial')),
        ]

    def __str__(self):
        if self.entrega_epi_id:
            return f"Inspeção de {self.entrega_epi} em {self.data_agendada}"
        if self.equipamento_id:
            return f"Inspeção de {self.equipamento.nome} em {self.data_agendada}"
        return f"Inspeção (ID: {self.pk}) em {self.data_agendada}"

    def save(self, *args, **kwargs):
        if self.entrega_epi_id:
            if not self.equipamento_id:
                self.equipamento_id = self.entrega_epi.equipamento_id
            if not self.filial_id:  # bug anterior: self.filial_ativa
                self.filial_id = self.entrega_epi.filial_id
        if not self.equipamento_id and not self.entrega_epi_id:
            raise ValueError('A inspeção deve estar ligada a um Equipamento ou a uma Entrega de EPI.')
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('gestao_riscos:inspecao_detalhe', kwargs={'pk': self.pk})


class CartaoTag(models.Model):
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name='cartoes_tag',
        verbose_name='Funcionário Proprietário',
    )
    cargo = models.ForeignKey(
        Cargo, on_delete=models.SET_NULL, related_name='cartoes_tag',
        null=True, blank=True,
    )
    # Telefone CORPORATIVO (não coletar celular pessoal — minimização LGPD)
    fone = models.CharField('Telefone de Contato', max_length=20, default='(11) 3045-9400')
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_validade = models.DateField('Data de Validade', null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='cartoes_tag')

    objects = FilialManager()

    class Meta:
        verbose_name = 'Cartão de Bloqueio (Tag)'
        verbose_name_plural = 'Cartões de Bloqueio (Tags)'
        ordering = ['-data_criacao']
        permissions = [
            ('view_all_cartaotag', _('Pode visualizar todos os cartões de bloqueio da filial')),
        ]

    def __str__(self):
        return f"Cartão de {self.funcionario.nome_completo}"


class TipoRisco(models.Model):
    CORES_CATEGORIA = {
        'fisico': '#00a651',
        'quimico': '#ed1c24',
        'biologico': '#8B4513',
        'ergonomico': '#f7ec13',
        'acidente': '#0068b7',
    }
    COR_PADRAO = '#808080'

    categoria = models.CharField('Categoria', max_length=20, choices=CATEGORIA_RISCO_CHOICES)
    nome = models.CharField('Nome do Risco', max_length=200)
    descricao = models.TextField('Descrição', blank=True)
    codigo_cor = models.CharField(
        'Código da Cor', max_length=7, default=COR_PADRAO, validators=[hex_color_validator],
    )
    nr_referencia = models.CharField('NR de Referência', max_length=50, blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='tipos_risco')

    objects = FilialManager()

    class Meta:
        db_table = 'gestao_tipo_risco'
        verbose_name = 'Tipo de Risco'
        verbose_name_plural = 'Tipos de Riscos'
        ordering = ['categoria', 'nome']
        constraints = [
            models.UniqueConstraint(fields=['categoria', 'nome', 'filial'],
                                    name='uniq_tiporisco_cat_nome_filial'),
        ]

    def __str__(self):
        return f"{self.get_categoria_display()} - {self.nome}"

    def get_cor_categoria(self):
        return self.CORES_CATEGORIA.get(self.categoria, self.COR_PADRAO)

    def save(self, *args, **kwargs):
        if not self.codigo_cor or self.codigo_cor == self.COR_PADRAO:
            self.codigo_cor = self.get_cor_categoria()
        super().save(*args, **kwargs)


# ── Invalidação do cache do contador "dias sem acidentes" ──
def dias_sem_acidentes_cache_key(filial_id):
    return f'gr:dias_sem_acidentes:{filial_id}'


@receiver([post_save, post_delete], sender=Incidente)
def _invalida_cache_dias(sender, instance, **kwargs):
    if instance.filial_id:
        cache.delete(dias_sem_acidentes_cache_key(instance.filial_id))

