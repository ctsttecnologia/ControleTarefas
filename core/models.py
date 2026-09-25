
import base64
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta
from django.conf import settings


class BaseModel(models.Model):
    """
    Um modelo base abstrato que outros modelos podem herdar.
    Ele fornece campos automáticos de data de criação e atualização.
    """
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        # Essencial: Isso diz ao Django para não criar uma tabela
        # no banco de dados para este modelo. Ele apenas serve de base.
        abstract = True
        ordering = ['-criado_em']


def caminho_assinatura(instance, filename):
    modelo = instance.__class__.__name__.lower()
    return f"assinaturas/{modelo}/{instance.pk or uuid.uuid4()}.png"


class AssinavelMixin(models.Model):
    assinatura_imagem = models.ImageField(upload_to=caminho_assinatura, null=True, blank=True)
    data_assinatura = models.DateTimeField(null=True, blank=True)
    ip_assinatura = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        abstract = True

    def assinar_remotamente(self, post_data, files_data, ip=None):
        """
        Wrapper para uso na assinatura remota (via link/token).
        Reaproveita a lógica já existente de salvar_assinatura().
        """
        assinatura_base64 = post_data.get('assinatura_base64')
        imagem_upload = files_data.get('assinatura_imagem')

        if not assinatura_base64 and not imagem_upload:
            raise ValueError("Nenhuma assinatura foi enviada.")

        self.salvar_assinatura(
            assinatura_base64=assinatura_base64,
            imagem_upload=imagem_upload,
            ip=ip,
        )

    def pode_ser_assinado(self):
        return self.data_assinatura is None

    def salvar_assinatura(self, assinatura_base64=None, imagem_upload=None, ip=None):
        if not self.pode_ser_assinado():
            raise ValidationError("Este documento não pode receber assinatura no momento.")
        if not assinatura_base64 and not imagem_upload:
            raise ValidationError("Nenhuma assinatura foi informada.")

        if imagem_upload:
            self._validar_upload(imagem_upload)
            self.assinatura_imagem = imagem_upload
        else:
            self.assinatura_imagem = self._base64_para_arquivo(assinatura_base64)

        self.data_assinatura = timezone.now()
        self.ip_assinatura = ip
        self.save()

    @staticmethod
    def _validar_upload(imagem_upload, max_mb=2):
        tipos_validos = ('image/png', 'image/jpeg')
        if imagem_upload.content_type not in tipos_validos:
            raise ValidationError("Formato inválido. Envie apenas PNG ou JPEG.")
        if imagem_upload.size > max_mb * 1024 * 1024:
            raise ValidationError(f"Arquivo maior que {max_mb}MB.")

    def _base64_para_arquivo(self, assinatura_base64):
        try:
            formato, dados = assinatura_base64.split(';base64,')
            extensao = formato.split('/')[-1]
            return ContentFile(
                base64.b64decode(dados),
                name=f"assinatura_{uuid.uuid4().hex}.{extensao}",
            )
        except Exception:
            raise ValidationError("Assinatura inválida ou corrompida.")

def default_expira_em():

    return timezone.now() + timedelta(days=7)

class TokenAssinaturaRemota(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    conteudo = GenericForeignKey('content_type', 'object_id')

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField(default=default_expira_em)
    usado_em = models.DateTimeField(null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    ip_utilizacao = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['token'])]

    @classmethod
    def gerar(cls, instancia, usuario=None, horas_validade=48):
        return cls.objects.create(
            content_type=ContentType.objects.get_for_model(instancia),
            object_id=instancia.pk,
            expira_em=timezone.now() + timedelta(hours=horas_validade),
            criado_por=usuario,
        )

    @property
    def valido(self):
        return self.usado_em is None and self.expira_em >= timezone.now()

    def marcar_utilizado(self, ip=None):
        self.usado_em = timezone.now()
        self.ip_utilizacao = ip
        self.save(update_fields=['usado_em', 'ip_utilizacao'])
