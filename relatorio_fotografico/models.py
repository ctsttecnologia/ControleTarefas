# relatorio_fotografico/models.py
import logging
import math
from io import BytesIO

from cloudinary.models import CloudinaryField
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageOps

from core.mixins import sanitize_image

logger = logging.getLogger(__name__)

FOTOS_POR_PAGINA = 6  # 2 colunas x 3 linhas
FOTO_MAX_SIZE = (800, 600)
FOTO_QUALIDADE = 80


class RelatorioFotografico(models.Model):
    STATUS_RASCUNHO = 'rascunho'
    STATUS_PENDENTE = 'pendente'
    STATUS_FINALIZADO = 'finalizado'
    STATUS_CHOICES = [
        (STATUS_RASCUNHO, 'Rascunho'),
        (STATUS_PENDENTE, 'Pendente'),
        (STATUS_FINALIZADO, 'Finalizado'),
    ]

    titulo = models.CharField('Assunto', max_length=200)
    obra_contrato = models.CharField('Obra/Contrato', max_length=150)
    data = models.DateField('Data')
    empresa = models.CharField('Empresa', max_length=60, blank=True, default='Cetest')
    telefone = models.CharField('Telefone', max_length=20, blank=True, default='11 3045-9400')
    email = models.EmailField('E-mail', blank=True, default='')
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='relatorios_fotograficos_responsavel', verbose_name='Responsável',
    )
    filial = models.ForeignKey(
        'usuario.Filial', on_delete=models.PROTECT,
        related_name='relatorios_fotograficos', verbose_name='Filial',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RASCUNHO)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='relatorios_fotograficos_criados', editable=False,
    )
    assunto = models.CharField(max_length=455, blank=True, default='')
    observacoes = models.TextField('Observações', blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Relatório Fotográfico'
        verbose_name_plural = 'Relatórios Fotográficos'
        ordering = ['-data', '-created_at']
        permissions = [
            ('view_all_relatorios_filial',
             'Pode visualizar todos os relatórios fotográficos da filial'),
        ]

    def __str__(self):
        return f'{self.titulo} - {self.obra_contrato} ({self.data:%d/%m/%Y})'

    def get_absolute_url(self):
        return reverse('relatorio_fotografico:detail', args=[self.pk])

    @property
    def total_folhas(self):
        total = self.fotos.count()
        return max(1, math.ceil(total / FOTOS_POR_PAGINA))

    @property
    def paginas(self):
        fotos = list(self.fotos.all())
        return [fotos[i:i + FOTOS_POR_PAGINA]
                for i in range(0, len(fotos), FOTOS_POR_PAGINA)] or [[]]

    @property
    def paginas_em_linhas(self):
        resultado = []
        for pagina in self.paginas:
            linhas = [pagina[i:i + 2] for i in range(0, len(pagina), 2)]
            linhas += [[]] * (3 - len(linhas))
            resultado.append(linhas)
        return resultado

    @property
    def local(self):
        foto = self.fotos.exclude(endereco='').first()
        return foto.endereco if foto else ''

    @property
    def analise_ia(self):
        """Última análise consolidada concluída (usada no relatório)."""
        return (self.visoes
                .filter(foto__isnull=True, status=RelatorioVisao.STATUS_CONCLUIDO)
                .select_related('editado_por')
                .first())


class FotoRelatorio(models.Model):
    relatorio = models.ForeignKey(
        RelatorioFotografico, on_delete=models.CASCADE, related_name='fotos',
    )
    imagem = CloudinaryField(
        'imagem', folder='relatorios_fotograficos', resource_type='image', type='upload',
    )
    legenda = models.TextField('Descrição', blank=True)
    ordem = models.PositiveIntegerField('Ordem', default=0)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    endereco = models.CharField('Endereço', max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foto do Relatório'
        verbose_name_plural = 'Fotos do Relatório'
        ordering = ['ordem', 'id']

    def __str__(self):
        return f'Foto #{self.ordem} - {self.relatorio_id}'

    @property
    def tem_geolocalizacao(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def coordenadas_formatadas(self):
        if not self.tem_geolocalizacao:
            return ''
        return f'{float(self.latitude):.5f}, {float(self.longitude):.5f}'

    def save(self, *args, **kwargs):
        if isinstance(self.imagem, UploadedFile):
            self.imagem = self._padronizar_imagem(sanitize_image(self.imagem))

        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new and self.tem_geolocalizacao and not self.endereco:
            transaction.on_commit(self._agendar_geocodificacao)

    def _agendar_geocodificacao(self):
        try:
            from .tasks import preencher_endereco_foto
            preencher_endereco_foto.apply_async(args=[self.pk], retry=False)
        except Exception as exc:
            logger.warning('Geocodificação não agendada (foto %s): %s', self.pk, exc)

    @staticmethod
    def _padronizar_imagem(arquivo):
        arquivo.seek(0)
        img = ImageOps.exif_transpose(Image.open(arquivo))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img = ImageOps.fit(img, FOTO_MAX_SIZE, Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=FOTO_QUALIDADE, optimize=True)
        buffer.seek(0)

        nome_base = getattr(arquivo, 'name', 'foto.jpg').rsplit('.', 1)[0]
        return InMemoryUploadedFile(
            buffer, None, f'{nome_base}.jpg', 'image/jpeg',
            buffer.getbuffer().nbytes, None,
        )


class RelatorioVisao(models.Model):
    STATUS_AGUARDANDO = 'aguardando'
    STATUS_PROCESSANDO = 'processando'
    STATUS_CONCLUIDO = 'concluido'
    STATUS_ERRO = 'erro'
    STATUS_CHOICES = [
        (STATUS_AGUARDANDO, 'Aguardando'),
        (STATUS_PROCESSANDO, 'Processando'),
        (STATUS_CONCLUIDO, 'Concluído'),
        (STATUS_ERRO, 'Erro'),
    ]

    relatorio = models.ForeignKey(
        RelatorioFotografico, on_delete=models.CASCADE, related_name='visoes',
    )
    # NULL = análise consolidada; preenchido = análise de uma foto.
    foto = models.ForeignKey(
        FotoRelatorio, on_delete=models.CASCADE, null=True, blank=True, related_name='visoes',
    )
    execucao_id = models.CharField(max_length=100, null=True, blank=True)
    modelo = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_AGUARDANDO, db_index=True,
    )
    resultado = models.JSONField(null=True, blank=True)   # JSON original (auditoria)
    erro = models.TextField(blank=True, default='')
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='analises_relatorios_fotograficos',
    )
    versao_prompt = models.CharField(max_length=30, blank=True, default='v1')
    hash_entrada = models.CharField(max_length=64, blank=True, default='')

    # --- Texto editável exibido no relatório ---
    texto = models.TextField('Análise de IA', blank=True, default='')
    editado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='analises_ia_editadas', editable=False,
    )
    editado_em = models.DateTimeField(null=True, blank=True, editable=False)

    iniciado_em = models.DateTimeField(null=True, blank=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Análise de IA'
        verbose_name_plural = 'Análises de IA'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['relatorio', 'execucao_id'],
                condition=models.Q(execucao_id__isnull=False),
                name='uniq_visao_relatorio_execucao',
            ),
        ]
        indexes = [models.Index(fields=['relatorio', 'foto', 'status'])]

    def __str__(self):
        tipo = 'Relatório completo' if self.foto_id is None else f'Foto {self.foto_id}'
        return f'Análise {self.execucao_id} - {tipo} ({self.status})'

    @property
    def foi_editado(self):
        return self.editado_em is not None

    @property
    def modelo_utilizado(self):
        return self.modelo or (self.resultado or {}).get('modelo_utilizado', '')

    def gerar_texto(self):
        from .services.analise_texto import analise_para_texto
        return analise_para_texto(self.resultado or {})

    def regenerar_texto(self, save=True):
        self.texto = self.gerar_texto()
        self.editado_por = None
        self.editado_em = None
        if save:
            self.save(update_fields=['texto', 'editado_por', 'editado_em', 'updated_at'])

    def marcar_editado(self, usuario):
        self.editado_por = usuario
        self.editado_em = timezone.now()

    def save(self, *args, **kwargs):
        # Gera o texto automaticamente na 1ª vez que houver resultado.
        if self.resultado and not self.texto:
            self.texto = self.gerar_texto()
            if 'update_fields' in kwargs and kwargs['update_fields'] is not None:
                kwargs['update_fields'] = set(kwargs['update_fields']) | {'texto'}
        super().save(*args, **kwargs)

