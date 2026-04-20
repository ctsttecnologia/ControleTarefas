
# ferramentas/models.py
from django.core.exceptions import ValidationError
from django.db.models import Q
from core.managers import FilialManager 
from usuario.models import Filial, Usuario
from core.models import BaseModel
from cliente.models import Cliente
# ferramentas/models.py
import qrcode
from io import BytesIO
from django.conf import settings
from django.core.files import File
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from core.managers import FilialQuerySet, FilialManager
from departamento_pessoal.models import Funcionario

# =============================================================================
# QUERYSETS E MANAGERS CUSTOMIZADOS
# =============================================================================

class FerramentaQuerySet(FilialQuerySet):
    """QuerySet customizado com métodos de negócio para Ferramentas."""

    def ativas(self):
        """Exclui ferramentas descartadas."""
        return self.exclude(status=Ferramenta.Status.DESCARTADA)

    def disponiveis(self):
        """Ferramentas prontas para retirada."""
        return self.filter(status=Ferramenta.Status.DISPONIVEL)

    def em_uso(self):
        """Ferramentas em uso direto ou via mala."""
        return self.filter(
            Q(status=Ferramenta.Status.EM_USO) |
            Q(mala__status=MalaFerramentas.Status.EM_USO)
        )

    def com_qr_code(self):
        """Ferramentas que possuem QR Code gerado."""
        return self.filter(qr_code__isnull=False).exclude(qr_code='')

    def sem_qr_code(self):
        """Ferramentas que ainda não possuem QR Code."""
        return self.filter(Q(qr_code__isnull=True) | Q(qr_code=''))

    def ferramentas_disponiveis_para_mala(self, mala_instance_pk=None):
        """Ferramentas sem mala ou da mala atual (para edição)."""
        sem_mala = Q(mala__isnull=True)
        if mala_instance_pk:
            return self.filter(sem_mala | Q(mala__pk=mala_instance_pk)).distinct()
        return self.filter(sem_mala).distinct()


class FerramentaManager(FilialManager):
    """Manager que usa o FerramentaQuerySet."""

    def get_queryset(self):
        return FerramentaQuerySet(self.model, using=self._db)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return getattr(self.get_queryset(), name)


# =============================================================================
# MALA DE FERRAMENTAS
# =============================================================================

class MalaFerramentas(models.Model):
    """Kit/conjunto de ferramentas que podem ser retiradas juntas."""

    class Status(models.TextChoices):
        DISPONIVEL = 'disponivel', 'Disponível'
        EM_USO = 'em_uso', 'Em Uso'

    nome = models.CharField(max_length=100, verbose_name="Nome da Mala/Kit")
    codigo_identificacao = models.CharField(
        max_length=50, unique=True,
        verbose_name="Código de Identificação"
    )
    localizacao_padrao = models.CharField(max_length=100, verbose_name="Localização Padrão")
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.DISPONIVEL, db_index=True
    )
    quantidade = models.PositiveIntegerField(default=1, verbose_name="Quantidade de Itens")
    qr_code = models.ImageField(
        upload_to='qrcodes/malas/', blank=True,
        verbose_name="QR Code da Mala"
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='malas_ferramentas'
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Mala de Ferramentas"
        verbose_name_plural = "Malas de Ferramentas"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.codigo_identificacao})"

    def get_absolute_url(self):
        return reverse('ferramentas:mala_detail', kwargs={'pk': self.pk})

    @property
    def esta_disponivel(self):
        return self.status == self.Status.DISPONIVEL

    def save(self, *args, **kwargs):
        if self.codigo_identificacao and not self.qr_code:
            self._gerar_qr_code(f"MALA_ID:{self.codigo_identificacao}", prefix='qr_code_mala')
        super().save(*args, **kwargs)

    def _gerar_qr_code(self, data, prefix='qr_code'):
        """Gera QR Code e salva no campo qr_code."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10, border=4
        )
        qr.add_data(data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        qr_img.save(buffer, 'PNG')
        buffer.seek(0)

        fname = f'{prefix}-{self.codigo_identificacao}.png'
        self.qr_code.save(fname, File(buffer), save=False)


# =============================================================================
# FERRAMENTA
# =============================================================================

class Ferramenta(models.Model):
    """Ferramenta individual do estoque da empresa."""

    class Status(models.TextChoices):
        DISPONIVEL = 'disponivel', 'Disponível'
        EM_USO = 'em_uso', 'Em Uso'
        EM_MANUTENCAO = 'em_manutencao', 'Em Manutenção'
        DESCARTADA = 'descartada', 'Descartada'

    # Identificação
    nome = models.CharField(max_length=100, verbose_name="Nome da Ferramenta")
    patrimonio = models.CharField(
        max_length=50, unique=True, blank=True, null=True,
        verbose_name="Nº de Patrimônio"
    )
    codigo_identificacao = models.CharField(
        max_length=50, unique=True,
        verbose_name="Código de Identificação (Série/QR)"
    )

    # Especificações técnicas
    fabricante_marca = models.CharField(max_length=50, blank=True, null=True, verbose_name="Fabricante/Marca")
    modelo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Modelo")
    serie = models.CharField(max_length=50, blank=True, null=True, verbose_name="Série")
    tamanho_polegadas = models.CharField(max_length=20, blank=True, null=True, verbose_name="Tamanho/Polegada")
    numero_laudo_tecnico = models.CharField(max_length=20, blank=True, null=True, verbose_name="Nº Laudo Técnico")

    # Controle
    quantidade = models.PositiveIntegerField(default=0, verbose_name="Quantidade")
    localizacao_padrao = models.CharField(
        max_length=100, verbose_name="Localização Padrão",
        help_text="Ex: Armário A, Gaveta 3"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.DISPONIVEL, verbose_name="Status Interno",
        db_index=True
    )

    # Datas
    data_aquisicao = models.DateField(verbose_name="Data de Aquisição")
    data_descarte = models.DateField(blank=True, null=True, verbose_name="Data de Descarte")

    # Texto livre
    observacoes = models.TextField(blank=True, null=True)

    # Arquivos
    qr_code = models.ImageField(upload_to='qrcodes/ferramentas/', blank=True, verbose_name="QR Code")

    # Relacionamentos
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='ferramentas', null=True
    )
    fornecedor = models.ForeignKey(
        'suprimentos.Parceiro', on_delete=models.SET_NULL,
        related_name='ferramentas_fornecidas',
        null=True, blank=True,
        verbose_name="Fornecedor Principal"
    )
    mala = models.ForeignKey(
        MalaFerramentas, on_delete=models.SET_NULL,
        related_name='itens',
        null=True, blank=True,
        verbose_name="Mala de Ferramentas"
    )

    objects = FerramentaManager()

    class Meta:
        verbose_name = "Ferramenta"
        verbose_name_plural = "Ferramentas"
        ordering = ['nome']
        indexes = [
            models.Index(fields=['status', 'filial'], name='idx_ferramenta_status_filial'),
            models.Index(fields=['codigo_identificacao'], name='idx_ferramenta_codigo'),
        ]

    def __str__(self):
        identificador = self.patrimonio or self.codigo_identificacao
        return f"{self.nome} ({identificador})"

    def get_absolute_url(self):
        return reverse('ferramentas:ferramenta_detail', kwargs={'pk': self.pk})

    def get_scan_url(self):
        return reverse('ferramentas:resultado_scan', kwargs={'codigo_identificacao': self.codigo_identificacao})

    # --- Properties de status ---

    @property
    def status_efetivo(self):
        """Calcula o status real considerando mala e manutenção."""
        if self.status in (self.Status.DESCARTADA, self.Status.EM_MANUTENCAO):
            return self.status
        if self.mala and self.mala.status == MalaFerramentas.Status.EM_USO:
            return self.Status.EM_USO
        return self.status

    @property
    def get_status_efetivo_display(self):
        return dict(self.Status.choices).get(self.status_efetivo, self.status_efetivo)

    @property
    def esta_disponivel_para_retirada(self):
        return self.status_efetivo == self.Status.DISPONIVEL

    @property
    def esta_emprestada(self):
        return self.status_efetivo == self.Status.EM_USO

    @property
    def termo_ativo(self):
        """Retorna o termo de responsabilidade ativo, se houver."""
        if self.esta_emprestada:
            mov = self.movimentacoes.filter(data_devolucao__isnull=True).select_related('termo_responsabilidade').first()
            if mov and mov.termo_responsabilidade:
                return mov.termo_responsabilidade
        return None

    # --- Save com geração de QR Code ---

    def save(self, *args, **kwargs):
        identifier = self.codigo_identificacao or self.patrimonio
        if identifier and not self.qr_code:
            qr_url = f"{settings.SITE_URL}{self.get_scan_url()}" if hasattr(settings, 'SITE_URL') else self.get_scan_url()
            self._gerar_qr_code(qr_url)
        super().save(*args, **kwargs)

    def _gerar_qr_code(self, data):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10, border=4
        )
        qr.add_data(data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        qr_img.save(buffer, 'PNG')
        buffer.seek(0)

        fname = f'qr_code-{self.codigo_identificacao}.png'
        self.qr_code.save(fname, File(buffer), save=False)


# =============================================================================
# ATIVIDADE (LOG)
# =============================================================================

class Atividade(models.Model):
    """Registro de atividades/eventos sobre ferramentas e malas."""

    class TipoAtividade(models.TextChoices):
        CRIACAO = 'criacao', 'Criação do Registro'
        ALTERACAO = 'alteracao', 'Alteração de Dados'
        RETIRADA = 'retirada', 'Retirada'
        DEVOLUCAO = 'devolucao', 'Devolução'
        MANUTENCAO_INICIO = 'manutencao_inicio', 'Início da Manutenção'
        MANUTENCAO_FIM = 'manutencao_fim', 'Fim da Manutenção'
        DESCARTE = 'descarte', 'Descarte/Inativação'

    ferramenta = models.ForeignKey(
        Ferramenta, on_delete=models.CASCADE,
        related_name='atividades', null=True, blank=True
    )
    mala = models.ForeignKey(
        MalaFerramentas, on_delete=models.CASCADE,
        related_name='atividades', null=True, blank=True
    )
    tipo_atividade = models.CharField(max_length=20, choices=TipoAtividade.choices, db_index=True)
    descricao = models.CharField(max_length=255, help_text="Detalhes do evento.")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Usuário Responsável"
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data e Hora", db_index=True)
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='atividades_ferramentas', null=True
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Registro de Atividade"
        verbose_name_plural = "Registros de Atividades"
        ordering = ['-timestamp']

    def __str__(self):
        item = self.ferramenta or self.mala or "Sistema"
        return f"{self.get_tipo_atividade_display()} em {item}"

    @property
    def item_afetado(self):
        return self.ferramenta or self.mala


# =============================================================================
# MOVIMENTAÇÃO
# =============================================================================

class Movimentacao(models.Model):
    """Registro de retirada/devolução de ferramentas e malas."""

    class TipoUso(models.TextChoices):
        VOLANTE = 'volante', 'Volante/Diária'
        PERMANENTE = 'permanente', 'Permanente'

    # Item movimentado (um ou outro)
    ferramenta = models.ForeignKey(
        Ferramenta, on_delete=models.PROTECT,
        related_name="movimentacoes", null=True, blank=True
    )
    mala = models.ForeignKey(
        MalaFerramentas, on_delete=models.PROTECT,
        related_name="movimentacoes", null=True, blank=True
    )
    termo_responsabilidade = models.ForeignKey(
        'TermoDeResponsabilidade', on_delete=models.SET_NULL,
        related_name="movimentacoes_geradas",
        null=True, blank=True,
        verbose_name="Termo Associado"
    )

    # Retirada
    retirado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="ferramentas_retiradas",
        verbose_name="Retirado por"
    )
    tipo_uso = models.CharField(
        max_length=30, choices=TipoUso.choices,
        default=TipoUso.VOLANTE, verbose_name="Tipo de Uso"
    )
    data_retirada = models.DateTimeField(auto_now_add=True, db_index=True)
    data_devolucao_prevista = models.DateTimeField(verbose_name="Devolução Prevista")
    condicoes_retirada = models.TextField(
        verbose_name="Condições na Retirada",
        help_text="Descreva o estado do item."
    )
    assinatura_retirada = models.ImageField(
        upload_to='assinaturas/%Y/%m/',
        verbose_name="Assinatura de Retirada"
    )

    # Devolução
    data_devolucao = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Data de Devolução", db_index=True
    )
    recebido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="ferramentas_recebidas",
        blank=True, null=True, verbose_name="Recebido por"
    )
    condicoes_devolucao = models.TextField(blank=True, null=True, verbose_name="Condições na Devolução")
    assinatura_devolucao = models.ImageField(
        upload_to='assinaturas/%Y/%m/', blank=True, null=True,
        verbose_name="Assinatura de Devolução"
    )

    # Controle
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='movimentacoes', null=True
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ['-data_retirada']
        indexes = [
            models.Index(fields=['data_devolucao', 'ferramenta'], name='idx_mov_dev_ferramenta'),
            models.Index(fields=['data_devolucao', 'mala'], name='idx_mov_dev_mala'),
        ]

    def __str__(self):
        item = self.item_movimentado
        if item:
            return f"Retirada de '{item}' por {self.retirado_por.get_username()}"
        return f"Movimentação #{self.pk}"

    @property
    def item_movimentado(self):
        return self.ferramenta or self.mala

    @property
    def esta_ativa(self):
        return self.data_devolucao is None

    @property
    def esta_atrasada(self):
        """Verifica se a devolução está atrasada."""
        if self.esta_ativa and self.data_devolucao_prevista:
            return timezone.now() > self.data_devolucao_prevista
        return False

    @property
    def dias_atraso(self):
        """Retorna dias de atraso (0 se não atrasado)."""
        if self.esta_atrasada:
            return (timezone.now() - self.data_devolucao_prevista).days
        return 0


# =============================================================================
# TERMO DE RESPONSABILIDADE
# =============================================================================

class TermoDeResponsabilidade(models.Model):
    """Documento formal de responsabilidade sobre ferramentas/malas."""

    class TipoUso(models.TextChoices):
        FERRAMENTAL = 'FER', 'Ferramental'
        MALA = 'MAL', 'Mala'

    class StatusTermo(models.TextChoices):
        ATIVO = 'ativo', 'Ativo'
        DEVOLVIDO = 'devolvido', 'Devolvido'
        ESTORNADO = 'estornado', 'Estornado'

    # Dados do termo
    contrato = models.CharField(max_length=200, verbose_name="Contrato")
    responsavel = models.ForeignKey(
        Funcionario, on_delete=models.PROTECT,
        related_name='termos_responsabilidade',
        verbose_name="Responsável"
    )
    separado_por = models.ForeignKey(
        Funcionario, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='termos_separados',
        verbose_name="Separado por (Coordenador)"
    )

    # Datas
    data_emissao = models.DateField(default=timezone.now, verbose_name="Data de Emissão")
    data_recebimento = models.DateTimeField(null=True, blank=True, verbose_name="Data de Recebimento")

    # Controle
    tipo_uso = models.CharField(max_length=30, choices=TipoUso.choices, verbose_name="Tipo de Uso")
    status = models.CharField(
        max_length=20, choices=StatusTermo.choices,
        default=StatusTermo.ATIVO, verbose_name="Status do Termo",
        db_index=True
    )
    assinatura_data = models.TextField(null=True, blank=True, verbose_name="Assinatura (Base64)")
    movimentado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        verbose_name="Movimentado por"
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT,
        related_name='termos_responsabilidade'
    )

    objects = FilialManager()

    class Meta:
        verbose_name = "Termo de Responsabilidade"
        verbose_name_plural = "Termos de Responsabilidade"
        ordering = ['-data_emissao']

    def __str__(self):
        return f"Termo #{self.pk} - {self.get_tipo_uso_display()} — {self.responsavel}"

    def is_signed(self):
        return bool(self.assinatura_data)

    @property
    def pode_reverter(self):
        """Verifica se o termo pode ser revertido."""
        if self.status != self.StatusTermo.ATIVO:
            return False
        return not self.movimentacoes_geradas.filter(data_devolucao__isnull=False).exists()

    @property
    def total_itens(self):
        return self.itens.count()


class ItemTermo(models.Model):
    """Linha individual na tabela do Termo de Responsabilidade."""

    termo = models.ForeignKey(
        TermoDeResponsabilidade, on_delete=models.CASCADE,
        related_name='itens', verbose_name="Termo"
    )
    quantidade = models.PositiveIntegerField(verbose_name="Quantidade")
    unidade = models.CharField(max_length=10, verbose_name="Unidade")
    item = models.CharField(max_length=255, verbose_name="Descrição do Item")
    ferramenta = models.ForeignKey(
        Ferramenta, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Ferramenta"
    )
    mala = models.ForeignKey(
        MalaFerramentas, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Mala"
    )

    class Meta:
        verbose_name = "Item do Termo"
        verbose_name_plural = "Itens do Termo"

    def __str__(self):
        return f"{self.item} ({self.quantidade} {self.unidade})"

    @property
    def item_vinculado(self):
        return self.ferramenta or self.mala

    