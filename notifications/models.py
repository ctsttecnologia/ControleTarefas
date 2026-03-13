# notifications/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone


class Notificacao(models.Model):
    """
    Sistema unificado de notificações.
    Qualquer módulo do sistema pode gerar notificações aqui.
    """

    # --- Tipos de notificação ---
    TIPO_CHOICES = [
        ('tarefa_atrasada', 'Tarefa Atrasada'),
        ('tarefa_lembrete', 'Lembrete de Tarefa'),
        ('tarefa_prazo_proximo', 'Prazo Próximo'),
        ('tarefa_status', 'Mudança de Status'),
        ('tarefa_criada', 'Tarefa Criada'),
        ('tarefa_atribuida', 'Tarefa Atribuída'),
        ('tarefa_comentario', 'Novo Comentário'),
        ('tarefa_concluida', 'Tarefa Concluída'),
        ('pgr_vencimento', 'PGR Próximo ao Vencimento'),
        ('pgr_criado', 'Novo PGR Criado'),
        ('pgr_risco_critico', 'Risco Crítico Identificado'),
        ('pgr_plano_atrasado', 'Plano de Ação Atrasado'),
        ('chat_mensagem', 'Nova Mensagem'),
        ('sistema', 'Notificação do Sistema'),
        # ══════ SUPRIMENTOS (NOVO) ══════
        ('pedido_pendente', 'Pedido Aguardando Aprovação'),
        ('pedido_aprovado', 'Pedido Aprovado'),
        ('pedido_reprovado', 'Pedido Reprovado'),
        ('pedido_entregue', 'Pedido Entregue'),
        ('pedido_recebido', 'Pedido Recebido'),
        ('pedido_verba_excedida', 'Pedido Excede Verba'),
    ]
    # --- Categorias (para agrupar/filtrar no dropdown) ---
    CATEGORIA_CHOICES = [
        ('tarefa', 'Tarefas'),
        ('pgr', 'PGR'),
        ('chat', 'Chat'),
        ('sistema', 'Sistema'),
        ('suprimentos', 'Suprimentos'),  # NOVO
    ]
    # --- Prioridade visual ---
    PRIORIDADE_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificacoes',
        verbose_name='Usuário',
    )
    tipo = models.CharField(
        'Tipo', max_length=30,
        choices=TIPO_CHOICES, default='sistema',
        db_index=True,
    )
    categoria = models.CharField(
        'Categoria', max_length=20,
        choices=CATEGORIA_CHOICES, default='sistema',
        db_index=True,
    )
    prioridade = models.CharField(
        'Prioridade', max_length=10,
        choices=PRIORIDADE_CHOICES, default='media',
    )
    titulo = models.CharField('Título', max_length=120, default='')
    mensagem = models.TextField('Mensagem', blank=True)
    lida = models.BooleanField('Lida', default=False, db_index=True)
    enviada_email = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    url_destino = models.CharField(
        'URL de Destino', max_length=500,
        blank=True, null=True,
        help_text='URL relativa do Django (ex: /tarefas/42/)',
    )
    icone = models.CharField(
        'Ícone Bootstrap', max_length=50,
        default='bi-bell',
        help_text='Classe do Bootstrap Icons (ex: bi-check-circle)',
    )
    data_criacao = models.DateTimeField('Criada em', auto_now_add=True)
    data_leitura = models.DateTimeField('Lida em', blank=True, null=True)
    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        indexes = [
            models.Index(fields=['usuario', 'lida']),
            models.Index(fields=['usuario', 'categoria', 'lida']),
            models.Index(fields=['-data_criacao']),
        ]
    def __str__(self):
        status = '✔' if self.lida else '◉'
        return f"{status} {self.titulo} → {self.usuario.username}"
    def marcar_como_lida(self):
        if not self.lida:
            self.lida = True
            self.data_leitura = timezone.now()
            self.save(update_fields=['lida', 'data_leitura'])
    @property
    def badge_class(self):
        """Retorna a classe CSS do badge conforme prioridade."""
        mapa = {
            'baixa': 'bg-secondary-subtle text-secondary-emphasis',
            'media': 'bg-info-subtle text-info-emphasis',
            'alta': 'bg-warning-subtle text-warning-emphasis',
            'critica': 'bg-danger-subtle text-danger-emphasis',
        }
        return mapa.get(self.prioridade, 'bg-secondary')
    @property
    def tempo_relativo(self):
        """Retorna tempo relativo (ex: 'há 5 min', 'há 2h')."""
        delta = timezone.now() - self.data_criacao
        segundos = int(delta.total_seconds())
        if segundos < 60:
            return 'agora'
        elif segundos < 3600:
            minutos = segundos // 60
            return f'há {minutos} min'
        elif segundos < 86400:
            horas = segundos // 3600
            return f'há {horas}h'
        else:
            dias = segundos // 86400
            return f'há {dias}d'

