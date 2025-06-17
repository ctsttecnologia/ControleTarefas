from datetime import timedelta
import logging
from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

logger = logging.getLogger(__name__)
User = get_user_model()

class Tarefas(models.Model):
    
    PRIORIDADE_CHOICES = [
        ('alta', _('Alta')),
        ('media', _('Média')),
        ('baixa', _('Baixa')),
    ]

    STATUS_CHOICES = [
        (1, 'pendente', _('Pendente')),
        (2, 'andamento', _('Em Andamento')),  
        (3, 'concluida', _('Concluído')),
        (4, 'cancelada', _('Cancelado')),
        (5, 'pausada', _('Em Pausa')),       
        (7, 'arquivada', _('Arquivada')),    
    ]
    STATUS_CHOICES = [(code, label) for _, code, label in STATUS_CHOICES]
    
    # Campos principais
    titulo = models.CharField(
        max_length=100,
        verbose_name=_('Título'),
        help_text=_('Título descritivo da tarefa')
    )
    
    descricao = models.TextField(
        verbose_name=_('Descrição'),
        blank=True,
        null=True,
        help_text=_('Detalhes completos da tarefa')
    )
    
    # Datas e prazos
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Data de Criação')
    )
    
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Atualização')
    )
    
    data_inicio = models.DateTimeField(
        default=timezone.now,  # Definindo valor padrão como agora
        verbose_name=_('Data de Início'),
        help_text=_('Data inicial da atividade')
    )
    
    prazo = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Prazo Final'),
        help_text=_('Data e hora limite para conclusão (formato: DD/MM/AAAA HH:MM)')
    )
    
    concluida_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Concluída em')
    )
    
    # Status e prioridade
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name=_('Status')
    )
    
    prioridade = models.CharField(
        max_length=20,
        choices=PRIORIDADE_CHOICES,
        default='media',
        verbose_name=_('Prioridade')
    )
    
    # Relacionamentos
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tarefas',
        verbose_name=_('Criado por'),
        editable=False  # Impede edição no admin/formulários
    )
    
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tarefas_responsavel',
        verbose_name=_('Responsável')
    )
    
    # Projeto e organização
    projeto = models.CharField(
        max_length=40,
        verbose_name=_('Projeto'),
        blank=True,
        null=True
    )
    
    # Tempo e controle - agora usando DurationField para melhor precisão
    duracao_prevista = models.DurationField(
        blank=True,
        null=True,
        verbose_name=_('Duração Prevista'),
        help_text=_('Formato: DD HH:MM:SS')
    )
    
    tempo_gasto = models.DurationField(
        blank=True,
        null=True,
        verbose_name=_('Tempo Gasto'),
        default=timedelta(0),
        help_text=_('Formato: DD HH:MM:SS')
    )
    
    # Campos de lembrete
    data_lembrete = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Data de Lembrete'),
        help_text=_('Data e hora para envio de lembrete')
    )
    
    dias_lembrete = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        verbose_name=_('Dias para Lembrete'),
        help_text=_('Dias antes do prazo para enviar lembrete (1-30)')
    )
    
    class Meta:
        verbose_name = _('Tarefa')
        verbose_name_plural = _('Tarefas')
        ordering = ['-prioridade', 'prazo']
        indexes = [
            models.Index(fields=['status'], name='idx_tarefa_status'),
            models.Index(fields=['prioridade'], name='idx_tarefa_prioridade'),
            models.Index(fields=['usuario'], name='idx_tarefa_usuario'),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Removemos a tentativa de pegar o usuário no __init__

    def clean(self):
        """Validações avançadas de datas e consistência"""
        if self.status not in dict(self.STATUS_CHOICES).keys():
            raise ValidationError({'status': 'Status inválido'})
        super().clean()
        
        now = timezone.now()
        
        # Validação de data_inicio
        if self.data_inicio and self.data_inicio < now - timedelta(minutes=5):
            raise ValidationError({
                'data_inicio': _('Data de início não pode ser no passado')
            })
        
        # Validação de prazo
        if self.prazo:
            if self.data_inicio and self.prazo < self.data_inicio:
                raise ValidationError({
                    'prazo': _('Prazo não pode ser anterior à data de início')
                })
            
            if self.prazo < now - timedelta(minutes=5):
                raise ValidationError({
                    'prazo': _('Prazo não pode ser no passado')
                })
        
        # Validação de concluida_em
        if self.concluida_em:
            if self.concluida_em < self.data_criacao:
                raise ValidationError({
                    'concluida_em': _('Data de conclusão não pode ser anterior à criação')
                })
            
            if self.prazo and self.concluida_em > self.prazo + timedelta(days=1):
                self.status = 'atrasada'
        
        # Configura data_lembrete automaticamente se não definida
        if self.prazo and not self.data_lembrete:
            self.data_lembrete = self.prazo - timedelta(days=self.dias_lembrete)
            
        # Validação de duração prevista
        if self.duracao_prevista and self.duracao_prevista.total_seconds() <= 0:
            raise ValidationError({
                'duracao_prevista': _('Duração deve ser maior que zero')
            })

    def save(self, *args, **kwargs):
        """Lógica avançada ao salvar a tarefa"""
        # Define o usuário atual como criador se for uma nova instância
        if not self.pk and not self.usuario_id:
            from django.contrib.auth.mixins import LoginRequiredMixin
            # O usuário deve ser passado como argumento ou obtido de outra forma
            # Removemos a tentativa de pegar o usuário diretamente aqui
        
        # Garante data_inicio padrão se não informada
        if not self.data_inicio:
            self.data_inicio = timezone.now()
        
        # Atualiza status de conclusão
        if self.status == 'concluida' and not self.concluida_em:
            self.concluida_em = timezone.now()
        elif self.status != 'concluida':
            self.concluida_em = None
        
        # Verifica atraso automaticamente
        if (self.prazo and self.prazo < timezone.now() and 
            self.status not in ['concluida', 'cancelada']):
            self.status = 'atrasada'
        
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def dias_restantes(self):
        """Retorna dias restantes para o prazo de forma segura"""
        if not self.prazo:
            return None
        try:
            delta = (self.prazo - timezone.now()).days
            return max(0, delta) if delta > 0 else abs(delta)
        except Exception:
            return None

    @property
    def progresso(self):
        """Calcula progresso com tratamento de erros"""
        try:
            if not all([self.duracao_prevista, self.tempo_gasto]):
                return 0
                
            total_previsto = self.duracao_prevista.total_seconds()
            total_gasto = self.tempo_gasto.total_seconds()
            
            if total_previsto <= 0:
                return 0
                
            progresso = (total_gasto / total_previsto) * 100
            return min(100, int(progresso))
        except Exception:
            return 0

    def __str__(self):
        return f"{self.titulo} ({self.get_status_display()})"
    
    class Meta:
        verbose_name = _('Tarefa')
        verbose_name_plural = _('Tarefas')
        ordering = ['-prioridade', 'prazo']
        indexes = [
            models.Index(fields=['status'], name='idx_tarefa_status'),
            models.Index(fields=['prioridade'], name='idx_tarefa_prioridade'),
            models.Index(fields=['usuario'], name='idx_tarefa_usuario'),
        ]

class Comentario(models.Model):
    tarefa = models.ForeignKey(
        Tarefas, on_delete=models.CASCADE, 
        related_name='comentarios'
    )
    
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('Autor')
    )
    
    texto = models.TextField(
        verbose_name=_('Comentário')
    )
    
    anexo = models.FileField(
        upload_to='comentarios/%Y/%m/',
        null=True,
        blank=True,
        verbose_name=_('Anexo')
    )
    
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Criado em')
    )
    
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Atualizado em')
    )

    # Métodos avançados
    @property
    def texto_resumido(self):
        """Retorna versão resumida do texto"""
        return f"{self.texto[:50]}..." if len(self.texto) > 50 else self.texto
    
    def __str__(self):
        return f"Comentário de {self.autor} em {self.tarefa}"
    
    class Meta:
        verbose_name = _('Comentário')
        verbose_name_plural = _('Comentários')
        ordering = ['-criado_em']

class HistoricoStatus(models.Model):
    tarefa = models.ForeignKey(
        Tarefas,
        on_delete=models.CASCADE,
        related_name='historicos',
        verbose_name=_('Tarefa')
    )
    
    status_anterior = models.CharField(
        max_length=20,
        verbose_name=_('Status Anterior')
    )
    
    novo_status = models.CharField(
        max_length=20,
        verbose_name=_('Novo Status')
    )
    
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('Alterado por')
    )
    
    data_alteracao = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Data da Alteração')
    )
    
    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Observação')
    )

    # Métodos avançados
    def tempo_decorrido(self):
        """Calcula tempo desde a alteração"""
        return timezone.now() - self.data_alteracao
    
    def __str__(self):
        return f"{self.tarefa} - {self.status_anterior} → {self.novo_status}"
    
    class Meta:
        verbose_name = _('Histórico de Status')
        verbose_name_plural = _('Históricos de Status')
        ordering = ['-data_alteracao']

