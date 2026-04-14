# documentos/models.py

import os
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from usuario.models import Filial
from core.managers import FilialManager
from core.upload import delete_old_file, safe_delete_file   # ← novo
from core.validators import SecureFileValidator              # ← novo
from documentos.storage import PrivateMediaStorage

private_storage = PrivateMediaStorage()


def private_document_path(instance, filename):
    """
    Upload seguro: /private_media/documentos/<app_label>/<object_id>/<filename>
    Se não tiver content_type (documento avulso), salva em /private_media/documentos/empresa/<id>/
    """
    if instance.content_type:
        app_label = instance.content_type.app_label
        obj_id    = instance.object_id or 0
    else:
        app_label = 'empresa'
        obj_id    = instance.pk or 0
    return f'documentos/{app_label}/{obj_id}/{filename}'


class Documento(models.Model):
    """
    Modelo UNIFICADO para gestão de documentos.

    Pode funcionar de 2 formas:
    1. ANEXADO a outro modelo (Funcionário, Treinamento, etc.) via GenericForeignKey
    2. INDEPENDENTE (documentos da empresa: contratos, alvarás, certidões)
       → Nesse caso content_type e object_id ficam NULL
    """

    # ══════════════════════════════════════════════
    # CHOICES
    # ══════════════════════════════════════════════

    class StatusChoices(models.TextChoices):
        VIGENTE   = 'VIGENTE',   'Vigente'
        A_VENCER  = 'A_VENCER',  'A Vencer'
        VENCIDO   = 'VENCIDO',   'Vencido'
        RENOVADO  = 'RENOVADO',  'Renovado/Inativo'
        ARQUIVADO = 'ARQUIVADO', 'Arquivado'

    class TipoChoices(models.TextChoices):
        CONTRATO    = 'CONTRATO',   'Contrato'
        ALVARA      = 'ALVARA',     'Alvará'
        CERTIDAO    = 'CERTIDAO',   'Certidão'
        FATURA      = 'FATURA',     'Fatura/Nota Fiscal'
        RELATORIO   = 'RELATORIO',  'Relatório'
        ART         = 'ART',        'ART'
        PGR         = 'PGR',        'PGR'
        LAUDO       = 'LAUDO',      'Laudo'
        CERTIFICADO = 'CERTIFICADO','Certificado'
        OUTROS      = 'OUTROS',     'Outros'

    # ══════════════════════════════════════════════
    # CAMPOS PRINCIPAIS
    # ══════════════════════════════════════════════

    nome      = models.CharField("Nome do Documento", max_length=255)
    tipo      = models.CharField(
        "Tipo de Documento",
        max_length=20,
        choices=TipoChoices.choices,
        default=TipoChoices.OUTROS,
    )
    descricao = models.TextField("Descrição/Observações", blank=True, default='')

    # ── Upload: mantém storage privado + path dinâmico, adiciona validator ───
    arquivo = models.FileField(
        verbose_name="Arquivo",
        upload_to=private_document_path,        # ← path dinâmico preservado
        storage=private_storage,                 # ← storage privado preservado
        validators=[SecureFileValidator('documentos')],   # ← novo
        help_text=_("O arquivo será armazenado em local seguro."),
    )
    # ─────────────────────────────────────────────────────────────────────────

    # ══════════════════════════════════════════════
    # DATAS E VENCIMENTO
    # ══════════════════════════════════════════════

    data_emissao    = models.DateField("Data de Emissão", null=True, blank=True)
    data_vencimento = models.DateField(
        "Data de Vencimento",
        null=True,
        blank=True,
        help_text="Deixe em branco se o documento não tiver vencimento.",
    )
    dias_aviso = models.PositiveIntegerField(
        "Avisar dias antes",
        default=30,
        help_text="Dias de antecedência para notificar vencimento.",
    )
    status = models.CharField(
        "Status",
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.VIGENTE,
    )

    # ══════════════════════════════════════════════
    # RELACIONAMENTOS
    # ══════════════════════════════════════════════

    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Responsável",
        related_name="documentos_responsaveis",
    )
    cliente = models.ForeignKey(
        'cliente.Cliente',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Cliente Relacionado",
        related_name="documentos_cliente",
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='documentos_filial',
        verbose_name="Filial",
        null=True,
    )

    # ══════════════════════════════════════════════
    # GENERIC FOREIGN KEY
    # ══════════════════════════════════════════════

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="Tipo de Objeto",
        null=True, blank=True,
    )
    object_id      = models.PositiveIntegerField("ID do Objeto", null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # ══════════════════════════════════════════════
    # RASTREAMENTO DE RENOVAÇÃO
    # ══════════════════════════════════════════════

    substitui = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="substituto",
        verbose_name="Substitui o Documento",
    )

    # ══════════════════════════════════════════════
    # TIMESTAMPS
    # ══════════════════════════════════════════════

    data_cadastro    = models.DateTimeField("Data de Cadastro", auto_now_add=True)
    data_atualizacao = models.DateTimeField("Data de Atualização", auto_now=True)

    # ══════════════════════════════════════════════
    # MANAGER
    # ══════════════════════════════════════════════

    objects = FilialManager()

    class Meta:
        verbose_name        = "Documento"
        verbose_name_plural = "Documentos"
        ordering            = ['data_vencimento']
        permissions = [
            ("pode_gerenciar_todos_documentos", "Pode gerenciar documentos de todas as filiais"),
            ("pode_validar_documento",          "Pode validar um documento enviado"),
        ]

    def __str__(self):
        tipo_display = self.get_tipo_display() if self.tipo != 'OUTROS' else ''
        return f"{self.nome} ({tipo_display})" if tipo_display else self.nome

    def get_absolute_url(self):
        return reverse('documentos:download', kwargs={'pk': self.pk})

    # ══════════════════════════════════════════════
    # GERENCIAMENTO DE ARQUIVO  ← novo
    # ══════════════════════════════════════════════

    def save(self, *args, **kwargs):
        # Substitui o arquivo antigo no storage privado ao editar
        delete_old_file(self, 'arquivo')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Remove o arquivo físico ao deletar o registro
        safe_delete_file(self, 'arquivo')
        super().delete(*args, **kwargs)

    # ══════════════════════════════════════════════
    # HELPERS / PROPERTIES
    # ══════════════════════════════════════════════

    @property
    def is_anexado(self):
        """True se está vinculado a outro modelo via GenericFK."""
        return self.content_type_id is not None and self.object_id is not None

    @property
    def is_avulso(self):
        """True se é documento independente (empresa/contrato)."""
        return not self.is_anexado

    def is_vencido(self):
        if not self.data_vencimento:
            return False
        return self.data_vencimento < timezone.now().date()

    @property
    def dias_para_vencer(self):
        if not self.data_vencimento:
            return None
        delta = (self.data_vencimento - timezone.now().date()).days
        return max(delta, 0)

