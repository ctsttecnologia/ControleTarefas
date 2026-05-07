# tarefas/models.py
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


User = settings.AUTH_USER_MODEL


class Tarefas(models.Model):
    """
    Modelo principal de Tarefas com suporte a recorrência hierárquica.
    
    Estrutura de recorrência:
    - Tarefa-RAIZ: recorrente=True, sem tarefa_recorrencia_pai
    - Tarefa-FILHA: recorrente=False, com tarefa_recorrencia_pai apontando para a raiz
    - Toda nova ocorrência é sempre filha da MESMA raiz (lista, não árvore)
    """

    STATUS_CHOICES = [
        ('pendente',   'Pendente'),
        ('andamento',  'Em Andamento'),
        ('pausada',    'Pausada'),
        ('concluida',  'Concluída'),
        ('atrasada',   'Atrasada'),
        ('cancelada',  'Cancelada'),
    ]

    PRIORIDADE_CHOICES = [
        ('baixa',  'Baixa'),
        ('normal', 'Normal'),
        ('media',  'Média'),
        ('alta',   'Alta'),
    ]

    FREQUENCIA_CHOICES = [
        ('diaria',     'Diária'),
        ('semanal',    'Semanal'),
        ('quinzenal',  'Quinzenal'),
        ('mensal',     'Mensal'),
        ('trimestral', 'Trimestral'),
        ('semestral',  'Semestral'),
        ('anual',      'Anual'),
    ]

    # 🆕 Constantes de segurança e configuração
    MAX_RECORRENCIAS_POR_RAIZ = 500
    DIAS_AVISO_FIM_PADRAO = 30

    # ─── Identificação ────────────────────────────────────────
    titulo      = models.CharField('Título', max_length=200)
    descricao   = models.TextField('Descrição', blank=True)
    ata_reuniao = models.TextField(
        'Atividade da Ata de Reunião',
        blank=True,
        help_text='Vincule a tarefa a uma ata ou reunião específica.',
    )

    # ─── Pessoas ──────────────────────────────────────────────
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tarefas_criadas',
        verbose_name='Criador',
    )
    responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tarefas_responsavel',
        verbose_name='Responsável',
    )
    participantes = models.ManyToManyField(
        User,
        blank=True,
        related_name='tarefas_participante',
        verbose_name='Participantes',
    )

    # ─── Filial ───────────────────────────────────────────────
    filial = models.ForeignKey(
        'usuario.Filial',
        on_delete=models.PROTECT,
        related_name='tarefas',
        verbose_name='Filial',
    )

    # ─── Organização ──────────────────────────────────────────
    projeto    = models.CharField('Projeto', max_length=100, blank=True)
    status     = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='pendente')
    prioridade = models.CharField('Prioridade', max_length=10, choices=PRIORIDADE_CHOICES, default='normal')

    # ─── Datas ────────────────────────────────────────────────
    data_criacao     = models.DateTimeField('Criada em', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Atualizada em', auto_now=True)
    data_inicio      = models.DateTimeField('Início', null=True, blank=True)
    prazo            = models.DateTimeField('Prazo', null=True, blank=True)
    concluida_em     = models.DateTimeField('Concluída em', null=True, blank=True)

    # ─── Estimativas ──────────────────────────────────────────
    duracao_prevista = models.DurationField(
        'Duração Prevista',
        null=True,
        blank=True,
        help_text='Formato: HH:MM:SS ou dias HH:MM:SS',
    )
    tempo_gasto = models.DurationField(
        'Tempo Gasto',
        null=True,
        blank=True,
        help_text='Tempo total trabalhado na tarefa.',
    )

    # ─── Lembrete ─────────────────────────────────────────────
    dias_lembrete = models.PositiveIntegerField(
        'Dias para Lembrete',
        default=0,
        help_text='Quantos dias antes do prazo enviar lembrete (0 = desativado).',
    )
    lembrete_enviado_em = models.DateTimeField(
        'Lembrete enviado em',
        null=True,
        blank=True,
        help_text='Controla envio único de lembrete.',
    )

    # ─── Recorrência ──────────────────────────────────────────
    recorrente = models.BooleanField(
        'Tarefa Recorrente',
        default=False,
        help_text='Se marcada, novas ocorrências serão geradas automaticamente.',
    )
    frequencia_recorrencia = models.CharField(
        'Frequência',
        max_length=20,
        choices=FREQUENCIA_CHOICES,
        blank=True,
    )
    data_fim_recorrencia = models.DateField(
        'Fim da Recorrência',
        null=True,
        blank=True,
        help_text='Após esta data, novas ocorrências não serão geradas.',
    )
    tarefa_recorrencia_pai = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorrencias_filhas',
        verbose_name='Tarefa-Raiz da Recorrência',
        help_text='Aponta para a tarefa original que gerou esta ocorrência.',
    )

    # 🆕 Novos campos para controle de recorrência
    dias_aviso_fim_recorrencia = models.PositiveIntegerField(
        'Dias para aviso de fim',
        default=DIAS_AVISO_FIM_PADRAO,
        help_text='Quantos dias antes do fim da recorrência avisar (padrão: 30).',
    )
    aviso_fim_enviado_em = models.DateTimeField(
        'Aviso de fim enviado em',
        null=True,
        blank=True,
        help_text='Controla envio único do aviso de fim de recorrência.',
    )
    recorrencia_encerrada = models.BooleanField(
        'Recorrência encerrada',
        default=False,
        help_text='Marca True quando a recorrência atingiu data_fim ou limite máximo.',
    )

    class Meta:
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'
        ordering = ['-data_criacao']
        permissions = [
            ('view_all_tarefas', 'Pode ver todas as tarefas (sem filtro)'),
        ]
        indexes = [
            models.Index(fields=['status', 'prazo']),
            models.Index(fields=['filial', 'status']),
            models.Index(fields=['recorrente', 'recorrencia_encerrada']),  # 🆕
            models.Index(fields=['tarefa_recorrencia_pai']),               # 🆕
        ]

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse('tarefas:tarefa_detail', kwargs={'pk': self.pk})

    # =========================================================
    # PROPRIEDADES
    # =========================================================

    @property
    def atrasada(self):
        """Retorna True se a tarefa está atrasada."""
        if not self.prazo or self.status in ('concluida', 'cancelada'):
            return False
        return timezone.now() > self.prazo

    @property
    def progresso(self):
        """Calcula progresso em % com base no status."""
        mapa = {
            'pendente':   0,
            'andamento':  50,
            'pausada':    25,
            'concluida':  100,
            'cancelada':  0,
            'atrasada':   50,
        }
        return mapa.get(self.status, 0)

    # 🆕 Propriedades de recorrência
    @property
    def is_raiz_recorrencia(self):
        """True se é uma tarefa-raiz de recorrência (não tem pai)."""
        return self.recorrente and self.tarefa_recorrencia_pai_id is None

    @property
    def is_filha_recorrencia(self):
        """True se é uma ocorrência gerada (tem pai)."""
        return self.tarefa_recorrencia_pai_id is not None

    @property
    def tarefa_raiz(self):
        """
        Retorna a tarefa-raiz desta cadeia.
        Se é raiz, retorna self. Se é filha, retorna o pai.
        """
        if self.is_filha_recorrencia:
            return self.tarefa_recorrencia_pai
        return self

    @property
    def total_ocorrencias_geradas(self):
        """Total de filhas geradas a partir desta raiz."""
        if not self.is_raiz_recorrencia:
            return self.tarefa_raiz.total_ocorrencias_geradas
        return self.recorrencias_filhas.count()

    @property
    def dias_para_fim_recorrencia(self):
        """Dias restantes até data_fim_recorrencia. None se não tem fim."""
        raiz = self.tarefa_raiz
        if not raiz.data_fim_recorrencia:
            return None
        delta = raiz.data_fim_recorrencia - timezone.localdate()
        return delta.days

    @property
    def proxima_data_recorrencia(self):
        """
        Calcula a próxima data de prazo (sem criar a tarefa).
        Útil para preview e validações.
        """
        return self._calcular_proximo_prazo()

    # =========================================================
    # MÉTODOS AUXILIARES — RECORRÊNCIA
    # =========================================================

    def _calcular_proximo_prazo(self, base_prazo=None):
        """
        Calcula a próxima data de prazo a partir de base_prazo
        (default: prazo desta tarefa) + frequência.
        """
        raiz = self.tarefa_raiz
        if not raiz.frequencia_recorrencia:
            return None

        base = base_prazo or self.prazo or timezone.now()

        delta_map = {
            'diaria':     timedelta(days=1),
            'semanal':    timedelta(weeks=1),
            'quinzenal':  timedelta(weeks=2),
            'mensal':     timedelta(days=30),
            'trimestral': timedelta(days=90),
            'semestral':  timedelta(days=180),
            'anual':      timedelta(days=365),
        }
        delta = delta_map.get(raiz.frequencia_recorrencia)
        return base + delta if delta else None

    def _ultima_ocorrencia_gerada(self):
        """
        Retorna a última filha gerada (mais recente por prazo).
        Se não há filhas, retorna a própria raiz.
        """
        raiz = self.tarefa_raiz
        ultima = raiz.recorrencias_filhas.order_by('-prazo', '-data_criacao').first()
        return ultima or raiz

    def pode_gerar_proxima(self):
        """
        Valida se é seguro gerar a próxima ocorrência.
        Retorna (bool, mensagem).
        """
        raiz = self.tarefa_raiz

        # 1. Recorrência precisa estar ativa
        if not raiz.recorrente:
            return False, 'Tarefa-raiz não é recorrente.'

        if raiz.recorrencia_encerrada:
            return False, 'Recorrência já foi encerrada.'

        if not raiz.frequencia_recorrencia:
            return False, 'Frequência não definida na tarefa-raiz.'

        # 2. Calcular próxima data
        ultima = self._ultima_ocorrencia_gerada()
        proxima_data = self._calcular_proximo_prazo(base_prazo=ultima.prazo)
        if not proxima_data:
            return False, 'Não foi possível calcular próxima data.'

        # 3. Verificar data_fim
        if raiz.data_fim_recorrencia:
            data_alvo = proxima_data.date() if hasattr(proxima_data, 'date') else proxima_data
            if data_alvo > raiz.data_fim_recorrencia:
                return False, 'Próxima data ultrapassa o fim da recorrência.'

        # 4. Limite de segurança
        if raiz.total_ocorrencias_geradas >= self.MAX_RECORRENCIAS_POR_RAIZ:
            return False, f'Limite máximo de {self.MAX_RECORRENCIAS_POR_RAIZ} ocorrências atingido.'

        return True, 'OK'

    def gerar_proxima_ocorrencia(self):
        """
        Gera a próxima ocorrência da recorrência.
        Sempre cria uma FILHA apontando para a tarefa-raiz.
        Retorna a nova tarefa criada ou None.
        """
        pode, motivo = self.pode_gerar_proxima()
        if not pode:
            # Se passou da data_fim ou atingiu limite, marca como encerrada
            raiz = self.tarefa_raiz
            if 'fim' in motivo.lower() or 'limite' in motivo.lower():
                if not raiz.recorrencia_encerrada:
                    Tarefas.objects.filter(pk=raiz.pk).update(
                        recorrencia_encerrada=True
                    )
            return None

        raiz = self.tarefa_raiz
        ultima = self._ultima_ocorrencia_gerada()
        novo_prazo = self._calcular_proximo_prazo(base_prazo=ultima.prazo)

        # Calcular novo data_inicio mantendo a diferença original
        novo_inicio = None
        if raiz.data_inicio and raiz.prazo:
            diff = raiz.prazo - raiz.data_inicio
            novo_inicio = novo_prazo - diff

        nova = Tarefas.objects.create(
            titulo=raiz.titulo,
            descricao=raiz.descricao,
            ata_reuniao=raiz.ata_reuniao,
            usuario=raiz.usuario,
            responsavel=raiz.responsavel,
            filial=raiz.filial,
            projeto=raiz.projeto,
            status='pendente',
            prioridade=raiz.prioridade,
            data_inicio=novo_inicio,
            prazo=novo_prazo,
            duracao_prevista=raiz.duracao_prevista,
            dias_lembrete=raiz.dias_lembrete,
            # 🔑 IMPORTANTE: filha NÃO é recorrente, só aponta para raiz
            recorrente=False,
            frequencia_recorrencia='',
            data_fim_recorrencia=None,
            tarefa_recorrencia_pai=raiz,
        )

        # Copiar participantes
        if raiz.participantes.exists():
            nova.participantes.set(raiz.participantes.all())

        return nova

    def encerrar_recorrencia(self, motivo=''):
        """Encerra a recorrência sem deletar tarefas."""
        raiz = self.tarefa_raiz
        Tarefas.objects.filter(pk=raiz.pk).update(
            recorrencia_encerrada=True,
        )

    def reativar_recorrencia(self, nova_data_fim=None, nova_frequencia=None):
        """
        Reativa uma recorrência encerrada (ou cria novo fluxo).
        Permite alterar data_fim e frequência ao reativar.
        """
        raiz = self.tarefa_raiz
        update_fields = {'recorrencia_encerrada': False}

        if nova_data_fim:
            update_fields['data_fim_recorrencia'] = nova_data_fim
        if nova_frequencia:
            update_fields['frequencia_recorrencia'] = nova_frequencia

        # Resetar aviso de fim para que seja enviado novamente se necessário
        update_fields['aviso_fim_enviado_em'] = None

        Tarefas.objects.filter(pk=raiz.pk).update(**update_fields)


# =============================================================================
# COMENTÁRIOS
# =============================================================================

class Comentario(models.Model):
    tarefa = models.ForeignKey(
        Tarefas,
        on_delete=models.CASCADE,
        related_name='comentarios',
    )
    autor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='comentarios_tarefas',
    )
    filial = models.ForeignKey(
        'usuario.Filial',
        on_delete=models.PROTECT,
        related_name='comentarios_tarefas',
        null=True,
        blank=True,
    )
    texto      = models.TextField('Comentário')
    anexo      = models.FileField('Anexo', upload_to='tarefas/comentarios/', blank=True, null=True)
    criado_em  = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.autor} em {self.tarefa}'


# =============================================================================
# HISTÓRICOS
# =============================================================================

class HistoricoStatus(models.Model):
    """Histórico legado — mantido para compatibilidade."""
    tarefa = models.ForeignKey(
        Tarefas,
        on_delete=models.CASCADE,
        related_name='historicos',
    )
    status_anterior  = models.CharField(max_length=20)
    novo_status      = models.CharField(max_length=20)
    alterado_por     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    filial = models.ForeignKey(
        'usuario.Filial',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    data_alteracao   = models.DateTimeField(auto_now_add=True)


class HistoricoTarefa(models.Model):
    """Histórico v2 — usado pelas views novas."""

    TIPO_ALTERACAO_CHOICES = [
        ('status',        'Mudança de Status'),
        ('participantes', 'Alteração de Participantes'),
        ('campo',         'Alteração de Campo'),
        ('comentario',    'Novo Comentário'),
        ('criacao',       'Criação'),
        ('exclusao',      'Exclusão'),
    ]

    tarefa = models.ForeignKey(
        'Tarefas',
        on_delete=models.CASCADE,
        related_name='historicos_v2',
    )
    alterado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    tipo_alteracao = models.CharField(
        max_length=30,
        choices=TIPO_ALTERACAO_CHOICES,
        default='campo',
        db_index=True,
    )
    filial = models.ForeignKey(
        'usuario.Filial',          # 👈 TROQUE pelo app correto (ex: 'empresas.Filial')
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historicos_tarefa',
    )
    campo_alterado  = models.CharField(max_length=50, blank=True)
    valor_anterior  = models.TextField(blank=True)
    valor_novo      = models.TextField(blank=True)
    descricao       = models.CharField(max_length=255, blank=True)
    data_alteracao  = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-data_alteracao']
        verbose_name = 'Histórico de Tarefa'
        verbose_name_plural = 'Históricos de Tarefas'
        permissions = [
            ('view_historico_tarefa', 'Pode ver histórico de tarefas'),
        ]
        

    def __str__(self):
        return f'#{self.tarefa_id} - {self.get_tipo_alteracao_display()}'