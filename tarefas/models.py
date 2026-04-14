
# tarefas/models.py

import logging
import os
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.managers import FilialManager
from core.upload import UploadPath, delete_old_file, safe_delete_file
from core.validators import SecureFileValidator
from usuario.models import Filial

logger = logging.getLogger(__name__)
User = settings.AUTH_USER_MODEL


# =============================================================================
# TAREFA
# =============================================================================
class Tarefas(models.Model):

    PRIORIDADE_CHOICES = [
        ('alta',  _('Alta')),
        ('media', _('Média')),
        ('baixa', _('Baixa')),
    ]

    STATUS_CHOICES = [
        ('concluida', _('Concluída')),
        ('andamento', _('Andamento')),
        ('pendente',  _('Pendente')),
        ('pausada',   _('Pausada')),
        ('atrasada',  _('Atrasada')),
        ('cancelada', _('Cancelada')),
    ]

    FREQUENCIA_CHOICES = [
        ('diaria',    _('Diária')),
        ('semanal',   _('Semanal')),
        ('quinzenal', _('Quinzenal')),
        ('mensal',    _('Mensal')),
        ('anual',     _('Anual')),
    ]

    # --- Campos Principais ---
    titulo    = models.CharField(_('Título'), max_length=100)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    status    = models.CharField(
        _('Status'), max_length=20, choices=STATUS_CHOICES, default='pendente'
    )
    prioridade = models.CharField(
        _('Prioridade'), max_length=10, choices=PRIORIDADE_CHOICES, default='baixa'
    )
    projeto = models.CharField(_('Projeto'), max_length=40, blank=True, null=True)

    # --- Datas ---
    data_criacao     = models.DateTimeField(_('Data de Criação'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)
    data_inicio      = models.DateTimeField(_('Data de Início'), blank=True, null=True)
    prazo            = models.DateTimeField(_('Prazo Final'), blank=True, null=True)
    concluida_em     = models.DateTimeField(_('Concluída em'), blank=True, null=True)

    # --- Duração ---
    duracao_prevista = models.DurationField(_('Duração Prevista'), null=True, blank=True)
    tempo_gasto      = models.DurationField(_('Tempo Gasto'), null=True, blank=True)

    # --- Lembrete ---
    dias_lembrete = models.PositiveSmallIntegerField(
        _('Lembrar-me quantos dias antes do prazo?'),
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        help_text=_('Deixe em branco se não desejar um lembrete automático.')
    )
    data_lembrete = models.DateTimeField(
        _('Data de Lembrete'), blank=True, null=True, editable=False
    )

    # --- Relacionamentos de Usuários ---
    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='tarefas_criadas', verbose_name=_('Criado por')
    )
    responsavel = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tarefas_responsavel', verbose_name=_('Responsável')
    )
    participantes = models.ManyToManyField(
        User, related_name='tarefas_participando',
        blank=True, verbose_name=_('Participantes')
    )

    # --- Recorrência ---
    recorrente = models.BooleanField(_('É uma tarefa recorrente?'), default=False)
    frequencia_recorrencia = models.CharField(
        _('Frequência'), max_length=10, choices=FREQUENCIA_CHOICES, blank=True, null=True
    )
    data_fim_recorrencia    = models.DateField(_('Repetir até'), blank=True, null=True)
    tarefa_recorrencia_pai  = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='recorrencias_filhas',
        verbose_name=_('Tarefa Original da Recorrência')
    )

    # --- Hierarquia (Subtarefas) ---
    tarefa_pai = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='subtarefas',
        verbose_name=_('Tarefa Principal')
    )

    # --- Relacionamentos Externos ---
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='tarefas', verbose_name=_('Filial'), null=True
    )
    ata_reuniao = models.ForeignKey(
        'ata_reuniao.ataReuniao',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tarefas_vinculadas',
        verbose_name=_('Atividade da Ata de Reunião'),
        help_text=_('Vincule esta tarefa a uma atividade de uma ata de reunião.')
    )

    objects = FilialManager()

    class Meta:
        verbose_name        = _('Tarefa')
        verbose_name_plural = _('Tarefas')
        ordering = ['-prioridade', 'prazo']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['prioridade']),
            models.Index(fields=['prazo']),
            models.Index(fields=['responsavel', 'status']),
        ]
        permissions = [
            ('view_dashboard',  'Pode ver o dashboard de tarefas'),
            ('view_relatorio',  'Pode ver relatórios de tarefas'),
            ('view_kanban',     'Pode ver o quadro Kanban'),
            ('view_calendario', 'Pode ver o calendário de tarefas'),
        ]

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse('tarefas:tarefa_detail', kwargs={'pk': self.pk})

    # --- Properties ---
    @property
    def atrasada(self):
        if self.prazo and self.status not in ('concluida', 'cancelada'):
            return timezone.now() > self.prazo
        return False

    @property
    def progresso(self):
        subtarefas = self.subtarefas.all()
        if subtarefas.exists():
            total     = subtarefas.count()
            concluidas = subtarefas.filter(status='concluida').count()
            return int((concluidas / total) * 100) if total > 0 else 0
        return 100 if self.status == 'concluida' else 0

    # --- Save ---
    def save(self, *args, **kwargs):
        usuario = getattr(self, '_user', None)
        is_new  = self.pk is None

        old_status = None
        if not is_new:
            try:
                old_status = Tarefas.objects.filter(pk=self.pk).values_list(
                    'status', flat=True
                ).first()
            except Exception:
                pass

        if not is_new and usuario:
            from tarefas.services import registrar_alteracoes_tarefa
            registrar_alteracoes_tarefa(self, usuario)

        # Calcula data do lembrete
        if self.prazo and self.dias_lembrete:
            self.data_lembrete = self.prazo - timedelta(days=self.dias_lembrete)
        else:
            self.data_lembrete = None

        # Auto-atrasada
        if (
            self.prazo
            and self.prazo < timezone.now()
            and self.status not in ('concluida', 'cancelada')
        ):
            self.status = 'atrasada'

        # Conclusão automática
        if self.status == 'concluida' and not self.concluida_em:
            self.concluida_em = timezone.now()
        elif self.status != 'concluida':
            self.concluida_em = None

        super().save(*args, **kwargs)

        if is_new and usuario:
            from tarefas.services import registrar_criacao_tarefa
            registrar_criacao_tarefa(self, usuario)

        if old_status and old_status != self.status and usuario:
            from tarefas.services import registrar_alteracao_status
            registrar_alteracao_status(
                tarefa=self,
                status_anterior_key=old_status,
                novo_status_key=self.status,
                alterado_por=usuario,
            )
            try:
                HistoricoTarefa.objects.create(
                    tarefa=self,
                    status_anterior=old_status,
                    novo_status=self.status,
                    alterado_por=usuario,
                    filial=self.filial,
                )
            except Exception:
                pass

        if (
            old_status
            and old_status != 'concluida'
            and self.status == 'concluida'
            and self.recorrente
        ):
            self._criar_proxima_recorrencia()

    def _criar_proxima_recorrencia(self):
        if not self.data_fim_recorrencia or timezone.now().date() >= self.data_fim_recorrencia:
            return
        if not self.data_inicio:
            return

        deltas = {
            'diaria':    relativedelta(days=1),
            'semanal':   relativedelta(weeks=1),
            'quinzenal': relativedelta(weeks=2),
            'mensal':    relativedelta(months=1),
            'anual':     relativedelta(years=1),
        }
        delta = deltas.get(self.frequencia_recorrencia)
        if not delta:
            return

        novo_inicio = self.data_inicio + delta
        if novo_inicio.date() > self.data_fim_recorrencia:
            return

        novo_prazo = (self.prazo + delta) if self.prazo else None

        Tarefas.objects.create(
            titulo=self.titulo,
            descricao=self.descricao,
            prioridade=self.prioridade,
            responsavel=self.responsavel,
            projeto=self.projeto,
            usuario=self.usuario,
            filial=self.filial,
            status='pendente',
            data_inicio=novo_inicio,
            prazo=novo_prazo,
            duracao_prevista=self.duracao_prevista,
            dias_lembrete=self.dias_lembrete,
            recorrente=True,
            frequencia_recorrencia=self.frequencia_recorrencia,
            data_fim_recorrencia=self.data_fim_recorrencia,
            tarefa_recorrencia_pai=self.tarefa_recorrencia_pai or self,
        )


# =============================================================================
# HISTÓRICO TAREFAS
# =============================================================================
class HistoricoTarefa(models.Model):

    TIPO_ALTERACAO_CHOICES = [
        ('criacao',            _('Criação')),
        ('status',             _('Mudança de Status')),
        ('participante_add',   _('Participante Adicionado')),
        ('participante_remove',_('Participante Removido')),
        ('responsavel',        _('Mudança de Responsável')),
        ('prioridade',         _('Mudança de Prioridade')),
        ('prazo',              _('Mudança de Prazo')),
        ('titulo',             _('Mudança de Título')),
        ('descricao',          _('Mudança de Descrição')),
        ('projeto',            _('Mudança de Projeto')),
        ('recorrencia',        _('Mudança de Recorrência')),
        ('geral',              _('Alteração Geral')),
    ]

    ICONE_MAP = {
        'criacao':             'bi-plus-circle-fill',
        'status':              'bi-arrow-repeat',
        'participante_add':    'bi-person-plus-fill',
        'participante_remove': 'bi-person-dash-fill',
        'responsavel':         'bi-person-check-fill',
        'prioridade':          'bi-flag-fill',
        'prazo':               'bi-calendar-event',
        'titulo':              'bi-pencil-fill',
        'descricao':           'bi-text-left',
        'projeto':             'bi-folder-fill',
        'recorrencia':         'bi-arrow-clockwise',
        'geral':               'bi-gear-fill',
    }

    COR_MAP = {
        'criacao':             '#22c55e',
        'status':              '#3b82f6',
        'participante_add':    '#0ea5e9',
        'participante_remove': '#f97316',
        'responsavel':         '#8b5cf6',
        'prioridade':          '#f59e0b',
        'prazo':               '#ef4444',
        'titulo':              '#6366f1',
        'descricao':           '#6366f1',
        'projeto':             '#14b8a6',
        'recorrencia':         '#8b5cf6',
        'geral':               '#6b7280',
    }

    tarefa = models.ForeignKey(
        Tarefas,
        on_delete=models.CASCADE,
        related_name='historicos_v2',
        verbose_name=_('Tarefa'),
    )
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Alterado por'),
    )
    tipo_alteracao = models.CharField(
        _('Tipo de Alteração'),
        max_length=25,
        choices=TIPO_ALTERACAO_CHOICES,
        default='status',
        db_index=True,
    )
    campo_alterado  = models.CharField(_('Campo Alterado'), max_length=50, blank=True, default='')
    valor_anterior  = models.TextField(_('Valor Anterior'), blank=True, default='')
    valor_novo      = models.TextField(_('Valor Novo'), blank=True, default='')
    descricao       = models.TextField(_('Descrição'), blank=True, default='')
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='historicos_tarefas_v2',
        verbose_name=_('Filial'),
        null=True, blank=True,
    )
    data_alteracao = models.DateTimeField(
        _('Data da Alteração'), auto_now_add=True, db_index=True,
    )

    class Meta:
        ordering = ['-data_alteracao']
        verbose_name        = _('Histórico da Tarefa')
        verbose_name_plural = _('Históricos das Tarefas')
        indexes = [
            models.Index(fields=['tarefa', '-data_alteracao']),
            models.Index(fields=['tipo_alteracao']),
        ]

    def __str__(self):
        if self.tipo_alteracao == 'status':
            return f'{self.valor_anterior} → {self.valor_novo}'
        return self.descricao[:80] or self.get_tipo_alteracao_display()

    @property
    def icone(self):
        return self.ICONE_MAP.get(self.tipo_alteracao, 'bi-gear-fill')

    @property
    def cor(self):
        return self.COR_MAP.get(self.tipo_alteracao, '#6b7280')

    # ── Compatibilidade com código antigo ──
    @property
    def status_anterior(self):
        return self.valor_anterior

    @property
    def novo_status(self):
        return self.valor_novo


# =============================================================================
# COMENTÁRIO
# =============================================================================
class Comentario(models.Model):

    tarefa = models.ForeignKey(
        Tarefas, on_delete=models.CASCADE,
        related_name='comentarios', verbose_name=_('Tarefa')
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name=_('Autor')
    )
    texto = models.TextField(_('Comentário'))

    # ── Upload seguro ─────────────────────────────────────────────────────────
    anexo = models.FileField(
        _('Anexo'),
        upload_to=UploadPath('tarefas'),
        blank=True,
        null=True,
        validators=[SecureFileValidator('tarefas')],
        help_text=_('PDF, imagens ou documentos Office. Máximo: 15MB.'),
    )
    # ─────────────────────────────────────────────────────────────────────────

    criado_em    = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now=True)
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='comentarios_tarefas',
        verbose_name=_('Filial'), null=True
    )

    objects = FilialManager()

    class Meta:
        verbose_name        = _('Comentário')
        verbose_name_plural = _('Comentários')
        ordering = ['-criado_em']

    def __str__(self):
        return f"Comentário em {self.tarefa} por {self.autor}"

    # ── Gerenciamento de arquivo ──────────────────────────────────────────────
    def save(self, *args, **kwargs):
        delete_old_file(self, 'anexo')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        safe_delete_file(self, 'anexo')
        super().delete(*args, **kwargs)
    # ─────────────────────────────────────────────────────────────────────────

    # ── Properties de conveniência (mantidas para templates existentes) ───────
    @property
    def nome_anexo(self):
        return os.path.basename(self.anexo.name) if self.anexo else None

    @property
    def extensao_anexo(self):
        if self.anexo:
            return os.path.splitext(self.anexo.name)[1][1:].lower()
        return None

    @property
    def tamanho_anexo_mb(self):
        return round(self.anexo.size / (1024 * 1024), 2) if self.anexo else 0



        