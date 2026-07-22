
# relatorio_fotografico/models.py
import math
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.urls import reverse
from PIL import Image, ImageOps
from core.mixins import make_upload_path, sanitize_image
from core.validators import SecureFileValidator

FOTOS_POR_PAGINA = 6  # 2 colunas x 3 linhas

# Tamanho máximo padronizado para as fotos do relatório
FOTO_MAX_SIZE = (800, 600)
FOTO_QUALIDADE = 80

class RelatorioFotografico(models.Model):

    STATUS_RASCUNHO = 'rascunho'
    STATUS_FINALIZADO = 'finalizado'
    STATUS_CHOICES = [
        (STATUS_RASCUNHO, 'Rascunho'),
        (STATUS_FINALIZADO, 'Finalizado'),
    ]

    titulo = models.CharField('Assunto', max_length=200)
    obra_contrato = models.CharField('Obra/Contrato', max_length=150)
    data = models.DateField('Data')
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
            # completa até 3 linhas
            while len(linhas) < 3:
                linhas.append([])
            resultado.append(linhas)
        return resultado


class FotoRelatorio(models.Model):

    relatorio = models.ForeignKey(
        RelatorioFotografico,
        on_delete=models.CASCADE,
        related_name='fotos',
    )
    imagem = models.ImageField(
        upload_to=make_upload_path('relatorio_fotografico'),
        validators=[SecureFileValidator('relatorio_fotografico')],
    )
    legenda = models.TextField('Descrição', blank=True)
    ordem = models.PositiveIntegerField('Ordem', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foto do Relatório'
        verbose_name_plural = 'Fotos do Relatório'
        ordering = ['ordem', 'id']

    def __str__(self):
        return f'Foto #{self.ordem} - {self.relatorio_id}'

    def save(self, *args, **kwargs):
        # Usa `_committed`: é False sempre que o arquivo é novo/alterado
        # e ainda não foi persistido no storage — funciona tanto para
        # InMemoryUploadedFile (arquivos pequenos) quanto para
        # TemporaryUploadedFile (arquivos grandes, ex.: fotos de celular
        # em alta resolução), evitando que uploads grandes escapem da
        # sanitização/padronização.
        if self.imagem and not self.imagem._committed:
            self.imagem.file = sanitize_image(self.imagem.file)
            self.imagem.file = self._padronizar_imagem(self.imagem.file)

        super().save(*args, **kwargs)


    def _padronizar_imagem(self, arquivo):
        arquivo.seek(0)
        img = Image.open(arquivo)
        img = ImageOps.exif_transpose(img)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Corta e redimensiona para proporção fixa 4:3 (uniformiza o grid)
        img = ImageOps.fit(img, FOTO_MAX_SIZE, Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=FOTO_QUALIDADE, optimize=True)
        buffer.seek(0)

        nome_original = getattr(arquivo, 'name', 'foto.jpg')
        nome_base = nome_original.rsplit('.', 1)[0]
        novo_nome = f'{nome_base}.jpg'

        return InMemoryUploadedFile(
            buffer, None, novo_nome, 'image/jpeg',
            buffer.getbuffer().nbytes, None,
        )


