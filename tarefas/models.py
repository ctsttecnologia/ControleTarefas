
from datetime import timedelta
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.html import format_html
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import F
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from dateutil.relativedelta import relativedelta
from core.managers import FilialManager
from usuario.models import Filial
import logging
import os


logger = logging.getLogger(__name__)

User = settings.AUTH_USER_MODEL

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

    recorrente = models.BooleanField(_('É uma tarefa recorrente?'), default=False)
    frequencia_recorrencia = models.CharField(
        _('Frequência'),
        max_length=10,
        choices=FREQUENCIA_CHOICES,
        blank=True,
        null=True
    )
    data_fim_recorrencia = models.DateField(_('Repetir até'), blank=True, null=True)
    tarefa_pai = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorrencias_filhas',
        verbose_name=_('Tarefa Original da Recorrência')
    )
    
    titulo = models.CharField(_('Título'), max_length=100)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    data_criacao = models.DateTimeField(_('Data de Criação'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)
    data_inicio = models.DateTimeField(_('Data de Início'), default=timezone.now)
    prazo = models.DateTimeField(_('Prazo Final'), blank=True, null=True)
    concluida_em = models.DateTimeField(_('Concluída em'), blank=True, null=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pendente')
    prioridade = models.CharField(
        max_length=10,
        choices=PRIORIDADE_CHOICES,
        default='baixo', # ou qualquer outro padrão
        verbose_name="Prioridade"
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tarefas_criadas', verbose_name=_('Criado por'))
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tarefas_responsavel', verbose_name=_('Responsável'))
    projeto = models.CharField(_('Projeto'), max_length=40, blank=True, null=True)
    duracao_prevista = models.DurationField(_('Duração Prevista'), null=True, blank=True)
    tempo_gasto = models.DurationField(_('Tempo Gasto'), null=True, blank=True)
    dias_lembrete = models.PositiveSmallIntegerField(
        _('Lembrar-me quantos dias antes do prazo?'), 
        null=True, 
        blank=True, 
        validators=[MinValueValidator(1)],
        help_text=_('Deixe em branco se não desejar um lembrete automático.')
    )
    data_lembrete = models.DateTimeField(
        _('Data de Lembrete'), 
        blank=True, 
        null=True, 
        editable=False # Impede que este campo apareça no ModelForm e no admin
    )
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT,
        related_name='tarefas',
        verbose_name="Filial",
        null=True
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()
    tarefa_pai = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtarefas',
        verbose_name='Tarefa Principal'
    )

    class Meta:
        verbose_name = _('Tarefa')
        verbose_name_plural = _('Tarefas')
        ordering = ['-prioridade', 'prazo']
        indexes = [models.Index(fields=['status']), models.Index(fields=['prioridade'])]

    def __str__(self):
        return self.titulo
    
    def get_absolute_url(self):
        return reverse('tarefas:tarefa_detail', kwargs={'pk': self.pk})

    @property
    def atrasada(self):
        if self.prazo and self.status not in ['concluida', 'cancelada']:
            return timezone.now() > self.prazo
        return False
 
    # MÉTODO SAVE FINAL E CENTRALIZADO
    def save(self, *args, **kwargs):
        # Captura o status antigo antes de salvar
        old_status = None
        if self.pk:
            try:
                old_status = Tarefas.objects.get(pk=self.pk).status
            except Tarefas.DoesNotExist:
                pass
        
        # Lógica para calcular a data do lembrete automaticamente
        if self.prazo and self.dias_lembrete:
            self.data_lembrete = self.prazo - timedelta(days=self.dias_lembrete)
        else:
            # Garante que a data do lembrete seja nula se não houver prazo ou dias
            self.data_lembrete = None

        # --- LÓGICA DE NEGÓCIO AUTOMÁTICA ---
        # 1. Atualiza status para 'atrasada' se necessário
        if self.prazo and self.prazo < timezone.now() and self.status not in ['concluida', 'cancelada']:
            self.status = 'atrasada'
        
        # 2. Preenche/limpa a data de conclusão
        if self.status == 'concluida' and not self.concluida_em:
            self.concluida_em = timezone.now()
        elif self.status != 'concluida' and self.concluida_em:
            self.concluida_em = None

        # 3. CRIA TAREFA RECORRENTE (LÓGICA CENTRALIZADA AQUI)
        # Se o status mudou para 'concluida' e a tarefa é recorrente...
        if old_status != 'concluida' and self.status == 'concluida' and self.recorrente:
            self._criar_proxima_recorrencia()

        super().save(*args, **kwargs)

        # 4. Cria registro de histórico se houve mudança de status
        if old_status and old_status != self.status and hasattr(self, '_user'):
            HistoricoStatus.objects.create(
                tarefa=self, status_anterior=old_status, novo_status=self.status,
                alterado_por=self._user,
            )
            
    @property
    def progresso(self):
        """
        Calcula o progresso da tarefa.
        - Se for uma tarefa principal, calcula com base nas subtarefas concluídas.
        - Se for uma subtarefa ou uma tarefa sem subtarefas, o progresso é 0% ou 100%.
        """
        # Verifica se é uma tarefa principal com subtarefas
        if self.subtarefas.exists():
            total_subtarefas = self.subtarefas.count()
            subtarefas_concluidas = self.subtarefas.filter(status='concluida').count()
            if total_subtarefas > 0:
                # Retorna a porcentagem como um número inteiro
                return int((subtarefas_concluidas / total_subtarefas) * 100)
            return 0 # Caso não hajam subtarefas (embora exists() já verifique)

        # Se não tiver subtarefas, o progresso é binário
        elif self.status == 'concluida':
            return 100
        else:
            return 0

    def _criar_proxima_recorrencia(self):
        """Cria a próxima ocorrência de uma tarefa recorrente."""
        from dateutil.relativedelta import relativedelta # Import local
        
        if not self.data_fim_recorrencia or timezone.now().date() >= self.data_fim_recorrencia:
            return

        frequencia = self.frequencia_recorrencia
        if frequencia == 'diaria': delta = relativedelta(days=1)
        elif frequencia == 'semanal': delta = relativedelta(weeks=1)
        elif frequencia == 'quinzenal': delta = relativedelta(weeks=2)
        elif frequencia == 'mensal': delta = relativedelta(months=1)
        else: return

        novo_inicio = self.data_inicio + delta
        if novo_inicio.date() > self.data_fim_recorrencia:
            return
            
        novo_prazo = (self.prazo + delta) if self.prazo else None

        # Cria a nova tarefa (sem o 'pk' para garantir que é um novo objeto)
        self.pk = None
        self.id = None
        self.status = 'pendente'
        self.concluida_em = None
        self.data_inicio = novo_inicio
        self.prazo = novo_prazo
        # Vincula à tarefa original (se já não estiver vinculada)
        self.tarefa_pai = self.tarefa_pai or self
        
        # Salva a nova instância da tarefa recorrente
        super().save()

class HistoricoStatus(models.Model):
    tarefa = models.ForeignKey(
        Tarefas,
        on_delete=models.CASCADE,
        related_name='historicos',
        verbose_name=_('Tarefa')
    )
    status_anterior = models.CharField(_('Status Anterior'), max_length=20)
    novo_status = models.CharField(_('Novo Status'), max_length=20)
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('Alterado por')
    )
    data_alteracao = models.DateTimeField(_('Data da Alteração'), auto_now_add=True)
    observacao = models.TextField(_('Observação'), blank=True, null=True)
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT,
        related_name='historicos_status', 
        verbose_name="Filial",
        null=True,                  
        blank=False              
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        verbose_name = _('Histórico de Status')
        verbose_name_plural = _('Históricos de Status')
        ordering = ['-data_alteracao']

    def __str__(self):
        return f"{self.tarefa} - {self.status_anterior} → {self.novo_status}"

class Comentario(models.Model):
    TAMANHO_MAXIMO_ANEXO = 5 * 1024 * 1024  # 5MB
    EXTENSOES_PERMITIDAS = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif']
    
    tarefa = models.ForeignKey(
        Tarefas,
        on_delete=models.CASCADE,
        related_name='comentarios',
        verbose_name=_('Tarefa')
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('Autor')
    )
    texto = models.TextField(_('Comentário'))
    anexo = models.FileField(
        _('Anexo'),
        upload_to='comentarios/%Y/%m/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=EXTENSOES_PERMITIDAS)
        ],
        help_text=format_html(
            "<span style='color:red;font-weight:bold;'>ATENÇÃO:</span> "
            "Arquivos podem conter vírus. Tipos permitidos: {} (Max {}MB)",
            ', '.join(EXTENSOES_PERMITIDAS),
            TAMANHO_MAXIMO_ANEXO // (1024*1024)
        )
    )
    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now=True)
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT,
        related_name='comentarios',
        verbose_name="Filial",
        null=True,                  
        blank=False              
    )
    # Manager customizado para segregação de dados
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
                        self.TAMANHO_MAXIMO_ANEXO // (1024*1024))
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
        return round(self.anexo.size / (1024*1024), 2) if self.anexo else 0

        