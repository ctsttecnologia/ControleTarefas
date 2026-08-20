
# relatorio_fotografico/models.py
import math
from io import BytesIO
from pyexpat import model

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile
from django.db import models
from django.urls import reverse
from PIL import Image, ImageOps

from cloudinary.models import CloudinaryField

from core.mixins import sanitize_image

from .services.geocoding import obter_endereco_por_coordenadas

FOTOS_POR_PAGINA = 6  # 2 colunas x 3 linhas

# Tamanho máximo padronizado para as fotos do relatório
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
    empresa = models.CharField('Empresa', max_length=60, blank=True, default='Cetest'
    )
    telefone = models.CharField('Telefone', max_length=20, blank=True, default='11 3045-9400')
    email = models.EmailField('E-mail', blank=True, default='') 
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='relatorios_fotograficos_responsavel',
        verbose_name='Responsável',
    )
    filial = models.ForeignKey(
        'usuario.Filial',
        on_delete=models.PROTECT,
        related_name='relatorios_fotograficos',
        verbose_name='Filial',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_RASCUNHO
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='relatorios_fotograficos_criados',
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    assunto = models.CharField(max_length=455, blank=True, default='')
    observacoes = models.TextField('Observações', blank=True, default='')

    class Meta:
        verbose_name = 'Relatório Fotográfico'
        verbose_name_plural = 'Relatórios Fotográficos'
        ordering = ['-data', '-created_at']
        permissions = [
            (
                'view_all_relatorios_filial',
                'Pode visualizar todos os relatórios fotográficos da filial',
            ),
        ]

    def __str__(self):
        return f'{self.titulo} - {self.obra_contrato} ({self.data:%d/%m/%Y})'

    def get_absolute_url(self):
        return reverse('relatorio_fotografico:detail', args=[self.pk])

    @property
    def total_folhas(self):
        total_fotos = self.fotos.count()
        if total_fotos == 0:
            return 1
        return math.ceil(total_fotos / FOTOS_POR_PAGINA)

    @property
    def paginas(self):
        """Retorna as fotos já paginadas em grupos de FOTOS_POR_PAGINA."""
        fotos = list(self.fotos.all().order_by('ordem', 'id'))
        return [
            fotos[i:i + FOTOS_POR_PAGINA]
            for i in range(0, len(fotos), FOTOS_POR_PAGINA)
        ] or [[]]

    @property
    def paginas_em_linhas(self):
        """Cada página já vem quebrada em linhas de 2 fotos."""
        resultado = []
        for pagina in self.paginas:
            linhas = [pagina[i:i + 2] for i in range(0, len(pagina), 2)]
            while len(linhas) < 3:
                linhas.append([])
            resultado.append(linhas)
        return resultado

    @property
    def local(self):
        """Endereço da primeira foto georreferenciada (com endereço já resolvido)."""
        foto = (
            self.fotos.exclude(endereco='')
            .order_by('ordem', 'id')
            .first()
        )
        return foto.endereco if foto else ''


class FotoRelatorio(models.Model):

    relatorio = models.ForeignKey(
        RelatorioFotografico,
        on_delete=models.CASCADE,
        related_name='fotos',
    )
    imagem = CloudinaryField(
        'imagem',
        folder='relatorios_fotograficos',
        resource_type='image',
        type='upload', 
    )
    legenda = models.TextField('Descrição', blank=True)
    ordem = models.PositiveIntegerField('Ordem', default=0)

    # --- Geolocalização (capturada no momento do upload) ---
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    endereco = models.CharField(
        'Endereço', max_length=255, blank=True, default=''
    )
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
        # CloudinaryField não encapsula o arquivo bruto em FieldFile na
        # atribuição (diferente do FileField nativo do Django), então
        # verificamos diretamente se ainda é um UploadedFile "cru".
        if isinstance(self.imagem, UploadedFile):
            arquivo_sanitizado = sanitize_image(self.imagem)
            self.imagem = self._padronizar_imagem(arquivo_sanitizado)

        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Dispara a geocodificação de forma assíncrona, sem travar o request
        if self.tem_geolocalizacao and not self.endereco:
            from .tasks import preencher_endereco_foto
            preencher_endereco_foto.delay(self.pk)

    def _padronizar_imagem(self, arquivo):
        """
        Redimensiona/recomprime a imagem para um tamanho e qualidade
        padronizados antes do upload para o Cloudinary.
        """
        arquivo.seek(0)
        img = Image.open(arquivo)
        img = ImageOps.exif_transpose(img)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        img = ImageOps.fit(img, FOTO_MAX_SIZE, Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=FOTO_QUALIDADE, optimize=True)
        buffer.seek(0)

        nome_original = getattr(arquivo, 'name', 'foto.jpg')
        nome_base = nome_original.rsplit('.', 1)[0]
        novo_nome = f'{nome_base}.jpg'

        return InMemoryUploadedFile(
            buffer,
            None,
            novo_nome,
            'image/jpeg',
            buffer.getbuffer().nbytes,
            None,
        )

