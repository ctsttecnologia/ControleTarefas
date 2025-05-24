from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class Tarefas(models.Model):
    PRIORIDADE_CHOICES = [
        ('alta', _('Alta')),
        ('media', _('Média')),
        ('baixa', _('Baixa')),
    ]

    STATUS_CHOICES = [
        ('pendente', _('Pendente')),
        ('andamento', _('Andamento')),
        ('concluida', _('Concluída')),
        ('cancelada', _('Cancelada')),
        ('pausada', _('Pausada')),
    ]
    
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
        default=timezone.now,
        verbose_name=_('Data de Início')
    )
    
    prazo = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('Prazo Final'),
        help_text=_('Data limite para conclusão')
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
        User,
        on_delete=models.CASCADE,
        related_name='tarefas',
        verbose_name=_('Criado por')
    )
    
    responsavel = models.ForeignKey(
        User,
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
    
    # Tempo e controle
    duracao_prevista = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('Duração Prevista (horas)'),
        validators=[MinValueValidator(1)]
    )
    
    tempo_gasto = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('Tempo Gasto (horas)'),
        default=0
    )
    
    # Métodos avançados
    def clean(self):
        """Validações personalizadas"""
        super().clean()
        
        # Validação de datas
        if self.prazo and self.prazo < timezone.now().date():
            raise ValidationError({
                'prazo': _('O prazo não pode ser uma data passada')
            })
        
        if self.concluida_em and self.concluida_em < self.data_criacao:
            raise ValidationError({
                'concluida_em': _('Data de conclusão não pode ser anterior à criação')
            })
    
    def save(self, *args, **kwargs):
        """Lógica adicional ao salvar"""
        # Atualiza status quando concluída
        if self.status == 'concluida' and not self.concluida_em:
            self.concluida_em = timezone.now()
        elif self.status != 'concluida':
            self.concluida_em = None
            
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def atrasada(self):
        """Verifica se a tarefa está atrasada"""
        if self.prazo and self.status not in ['concluida', 'cancelada']:
            return self.prazo < timezone.now().date()
        return False
    
    @property
    def progresso(self):
        """Calcula progresso baseado no tempo gasto"""
        if self.duracao_prevista and self.tempo_gasto:
            return min(100, int((self.tempo_gasto / self.duracao_prevista) * 100))
        return 0
    
    def registrar_historico(self, user, status_anterior):
        """Registra mudança de status no histórico"""
        if status_anterior != self.status:
            HistoricoStatus.objects.create(
                tarefa=self,
                status_anterior=status_anterior,
                novo_status=self.status,
                alterado_por=user
            )
    
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
        User,
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
        User,
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

