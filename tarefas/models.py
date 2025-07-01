
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


import logging
import os
from datetime import timedelta

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
    dias_lembrete = models.PositiveSmallIntegerField(_('Dias para Lembrete'), null=True, blank=True, validators=[MinValueValidator(1)])
    data_lembrete = models.DateTimeField(_('Data de Lembrete'), blank=True, null=True)

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

    # Unificando os dois métodos save() em um só.
    # MÉTODO SAVE UNIFICADO E LIMPO
    def save(self, *args, **kwargs):
        # Captura o status antigo antes de salvar
        old_status = None
        if self.pk:
            try:
                old_status = Tarefas.objects.get(pk=self.pk).status
            except Tarefas.DoesNotExist:
                pass
        
        # Lógica para definir o status como 'atrasada'
        if self.prazo and self.prazo < timezone.now() and self.status not in ['concluida', 'cancelada', 'atrasada']:
            self.status = 'atrasada'
        
        # Lógica para preencher/limpar a data de conclusão
        if self.status == 'concluida' and not self.concluida_em:
            self.concluida_em = timezone.now()
        elif self.status != 'concluida' and self.concluida_em:
            self.concluida_em = None
        
        super().save(*args, **kwargs)

        # Se houve mudança de status, cria um registro de histórico
        if old_status and old_status != self.status and hasattr(self, '_user'):
            HistoricoStatus.objects.create(
                tarefa=self,
                status_anterior=old_status,
                novo_status=self.status,
                alterado_por=self._user,
            )

    """def enviar_notificacao_prazo(self):
        if self.prazo and (self.prazo - timezone.now()).days <= 1:
            assunto = f"[Urgente] Tarefa {self.titulo} com prazo próximo"
            html_message = render_to_string('emails/notificacao_prazo.html', {
                'tarefa': self,
                'dias_restantes': (self.prazo - timezone.now()).days
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=assunto,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.responsavel.email],
                fail_silently=False
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.prazo:
            self.enviar_notificacao_prazo()
"""

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

        