
# tarefas/models.py

import logging
import os
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from core.managers import FilialManager
from usuario.models import Filial

logger = logging.getLogger(__name__)
User = settings.AUTH_USER_MODEL


# =============================================================================
# TAREFA
# =============================================================================
class Tarefas(models.Model):

    PRIORIDADE_CHOICES = [
        ('alta', _('Alta')),
        ('media', _('Média')),
        ('baixa', _('Baixa')),
    ]

    STATUS_CHOICES = [
        ('pendente', _('Pendente')),
        ('andamento', _('Andamento')),
        ('pausada', _('Pausada')),
        ('concluida', _('Concluída')),
        ('cancelada', _('Cancelada')),
        ('atrasada', _('Atrasada')),
    ]

    FREQUENCIA_CHOICES = [
        ('diaria', _('Diária')),
        ('semanal', _('Semanal')),
        ('quinzenal', _('Quinzenal')),
        ('mensal', _('Mensal')),
        ('anual', _('Anual')),
    ]

    # --- Campos Principais ---
    titulo = models.CharField(_('Título'), max_length=100)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    status = models.CharField(
        _('Status'), max_length=20,
        choices=STATUS_CHOICES, default='pendente'
    )
    prioridade = models.CharField(
        _('Prioridade'), max_length=10,
        choices=PRIORIDADE_CHOICES, default='baixa'  # ✅ Corrigido: era 'baixo'
    )
    projeto = models.CharField(_('Projeto'), max_length=40, blank=True, null=True)

    # --- Datas ---
    data_criacao = models.DateTimeField(_('Data de Criação'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)
    data_inicio = models.DateTimeField(_('Data de Início'), blank=True, null=True)
    prazo = models.DateTimeField(_('Prazo Final'), blank=True, null=True)
    concluida_em = models.DateTimeField(_('Concluída em'), blank=True, null=True)

    # --- Duração ---
    duracao_prevista = models.DurationField(_('Duração Prevista'), null=True, blank=True)
    tempo_gasto = models.DurationField(_('Tempo Gasto'), null=True, blank=True)

    # --- Lembrete ---
    dias_lembrete = models.PositiveSmallIntegerField(
        _('Lembrar-me quantos dias antes do prazo?'),
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        help_text=_('Deixe em branco se não desejar um lembrete automático.')
    )
    data_lembrete = models.DateTimeField(
        _('Data de Lembrete'),
        blank=True, null=True, editable=False
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
        _('Frequência'), max_length=10,
        choices=FREQUENCIA_CHOICES, blank=True, null=True
    )
    data_fim_recorrencia = models.DateField(_('Repetir até'), blank=True, null=True)
    tarefa_recorrencia_pai = models.ForeignKey(
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
        related_name='tarefas', verbose_name=_('Filial'),
        null=True
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
        verbose_name = _('Tarefa')
        verbose_name_plural = _('Tarefas')
        ordering = ['-prioridade', 'prazo']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['prioridade']),
            models.Index(fields=['prazo']),
            models.Index(fields=['responsavel', 'status']),
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
        """Calcula o progresso com base nas subtarefas."""
        subtarefas = self.subtarefas.all()
        if subtarefas.exists():
            total = subtarefas.count()
            concluidas = subtarefas.filter(status='concluida').count()
            return int((concluidas / total) * 100) if total > 0 else 0
        return 100 if self.status == 'concluida' else 0

    # --- Save ---
    def save(self, *args, **kwargs):
        # Captura status antigo
        old_status = None
        is_new = self.pk is None
        if not is_new:
            try:
                old_status = Tarefas.objects.filter(pk=self.pk).values_list('status', flat=True).first()
            except Tarefas.DoesNotExist:
                pass

        # Calcula data do lembrete
        if self.prazo and self.dias_lembrete:
            self.data_lembrete = self.prazo - timedelta(days=self.dias_lembrete)
        else:
            self.data_lembrete = None

        # Auto-atrasada
        if (self.prazo and self.prazo < timezone.now()
                and self.status not in ('concluida', 'cancelada')):
            self.status = 'atrasada'

        # Conclusão automática
        if self.status == 'concluida' and not self.concluida_em:
            self.concluida_em = timezone.now()
        elif self.status != 'concluida':
            self.concluida_em = None

        # ✅ Salva ANTES de criar recorrência (não corrompe self)
        super().save(*args, **kwargs)

        # Cria recorrência se status mudou para concluída
        if old_status and old_status != 'concluida' and self.status == 'concluida' and self.recorrente:
            self._criar_proxima_recorrencia()

        # Registra histórico
        if old_status and old_status != self.status and hasattr(self, '_user'):
            HistoricoStatus.objects.create(
                tarefa=self,
                status_anterior=old_status,
                novo_status=self.status,
                alterado_por=self._user,
                filial=self.filial,
            )

    def _criar_proxima_recorrencia(self):
        """Cria a próxima ocorrência SEM corromper self."""
        if not self.data_fim_recorrencia or timezone.now().date() >= self.data_fim_recorrencia:
            return
        if not self.data_inicio:
            return

        deltas = {
            'diaria': relativedelta(days=1),
            'semanal': relativedelta(weeks=1),
            'quinzenal': relativedelta(weeks=2),
            'mensal': relativedelta(months=1),
            'anual': relativedelta(years=1),
        }
        delta = deltas.get(self.frequencia_recorrencia)
        if not delta:
            return

        novo_inicio = self.data_inicio + delta
        if novo_inicio.date() > self.data_fim_recorrencia:
            return

        novo_prazo = (self.prazo + delta) if self.prazo else None

        # ✅ Cria um NOVO objeto sem modificar self
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
# HISTÓRICO DE STATUS
# =============================================================================
class HistoricoStatus(models.Model):
    tarefa = models.ForeignKey(
        Tarefas, on_delete=models.CASCADE,
        related_name='historicos', verbose_name=_('Tarefa')
    )
    status_anterior = models.CharField(_('Status Anterior'), max_length=20)
    novo_status = models.CharField(_('Novo Status'), max_length=20)
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name=_('Alterado por')
    )
    data_alteracao = models.DateTimeField(_('Data da Alteração'), auto_now_add=True)
    observacao = models.TextField(_('Observação'), blank=True, null=True)
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='historicos_status_tarefas',
        verbose_name=_('Filial'), null=True
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _('Histórico de Status')
        verbose_name_plural = _('Históricos de Status')
        ordering = ['-data_alteracao']

    def __str__(self):
        return f"{self.tarefa} — {self.status_anterior} → {self.novo_status}"


# =============================================================================
# COMENTÁRIO
# =============================================================================
class Comentario(models.Model):
    TAMANHO_MAXIMO_ANEXO = 5 * 1024 * 1024  # 5MB
    EXTENSOES_PERMITIDAS = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif']

    tarefa = models.ForeignKey(
        Tarefas, on_delete=models.CASCADE,
        related_name='comentarios', verbose_name=_('Tarefa')
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name=_('Autor')
    )
    texto = models.TextField(_('Comentário'))
    anexo = models.FileField(
        _('Anexo'),
        upload_to='comentarios/%Y/%m/',
        blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=EXTENSOES_PERMITIDAS)],
        help_text=format_html(
            "<span style='color:red;font-weight:bold;'>ATENÇÃO:</span> "
            "Tipos permitidos: {} (Max {}MB)",
            ', '.join(EXTENSOES_PERMITIDAS),
            TAMANHO_MAXIMO_ANEXO // (1024 * 1024)
        )
    )
    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now=True)
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='comentarios_tarefas',
        verbose_name=_('Filial'), null=True
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _('Comentário')
        verbose_name_plural = _('Comentários')
        ordering = ['-criado_em']

    def __str__(self):
        return f"Comentário em {self.tarefa} por {self.autor}"

    def clean(self):
        super().clean()
        if self.anexo:
            if self.anexo.size > self.TAMANHO_MAXIMO_ANEXO:
                raise ValidationError({
                    'anexo': _("Tamanho máximo excedido ({}MB)").format(
                        self.TAMANHO_MAXIMO_ANEXO // (1024 * 1024))
                })
            ext = os.path.splitext(self.anexo.name)[1][1:].lower()
            if ext not in self.EXTENSOES_PERMITIDAS:
                raise ValidationError({
                    'anexo': _("Extensão '{}' não permitida").format(ext)
                })

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


        