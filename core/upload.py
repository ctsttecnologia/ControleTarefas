
# core/upload.py

"""
Utilitários de upload seguro.

Contém:
    - UploadPath: classe callable para upload_to (serializável pelo Django)
    - sanitize_image: recodifica imagens removendo metadados EXIF
    - delete_old_file: remove arquivo antigo ao substituir campo FileField/ImageField
    - safe_delete_file: remove arquivo físico ao excluir registro
"""

import logging
import os
import uuid

from django.db import models
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# UPLOAD PATH (serializável pelo Django migrations)
# ═════════════════════════════════════════════════════════════════════════════

@deconstructible
class UploadPath:
    """
    Callable para `upload_to` que gera caminho seguro com UUID.

    Formato final:  uploads/<subfolder>/<uuid4_hex>.<ext>

    Benefícios:
        - Nome original do arquivo é descartado (sem path traversal)
        - UUID impede colisão e enumeração de arquivos
        - Extensão preservada para compatibilidade de Content-Type
        - @deconstructible permite serialização nas migrations

    Uso:
        foto = models.ImageField(upload_to=UploadPath('departamento_pessoal_foto'))
    """

    def __init__(self, subfolder: str):
        self.subfolder = subfolder

    def __call__(self, instance: models.Model, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        safe_name = f"{uuid.uuid4().hex}.{ext}"
        return f"uploads/{self.subfolder}/{safe_name}"

    def __eq__(self, other):
        return isinstance(other, UploadPath) and self.subfolder == other.subfolder


def make_upload_path(subfolder: str) -> UploadPath:
    """
    Factory function — atalho para UploadPath(subfolder).

    Mantém a mesma API usada nos models:
        upload_to=make_upload_path('departamento_pessoal_foto')
    """
    return UploadPath(subfolder)


# ═════════════════════════════════════════════════════════════════════════════
# SANITIZAÇÃO DE IMAGEM
# ═════════════════════════════════════════════════════════════════════════════

def sanitize_image(file_path: str) -> None:
    """
    Recodifica imagem removendo metadados EXIF e payloads embutidos.

    Abre a imagem com Pillow e salva novamente, descartando qualquer
    metadado ou chunk não-padrão. Funciona para JPEG, PNG e WebP.

    Args:
        file_path: caminho absoluto do arquivo no disco.

    Nota:
        - Se Pillow não estiver instalado, loga warning e retorna.
        - Se o arquivo não for imagem válida, loga warning e retorna.
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow não instalado — sanitização de imagem ignorada.")
        return

    if not os.path.isfile(file_path):
        logger.warning("sanitize_image: arquivo não encontrado — %s", file_path)
        return

    try:
        with Image.open(file_path) as img:
            # Remove perfil ICC e EXIF recriando a imagem "limpa"
            data = list(img.getdata())
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)

            # Determina formato pela extensão
            ext = file_path.rsplit(".", 1)[-1].lower()
            fmt_map = {
                "jpg": "JPEG",
                "jpeg": "JPEG",
                "png": "PNG",
                "webp": "WEBP",
            }
            fmt = fmt_map.get(ext, "JPEG")

            save_kwargs = {}
            if fmt == "JPEG":
                save_kwargs["quality"] = 85
                save_kwargs["optimize"] = True
            elif fmt == "WEBP":
                save_kwargs["quality"] = 85

            clean_img.save(file_path, format=fmt, **save_kwargs)

        logger.debug("Imagem sanitizada com sucesso: %s", file_path)

    except Exception:
        logger.warning("sanitize_image: falha ao sanitizar — %s", file_path, exc_info=True)


# ═════════════════════════════════════════════════════════════════════════════
# GERENCIAMENTO DE ARQUIVOS ANTIGOS
# ═════════════════════════════════════════════════════════════════════════════

def _file_uses_default_storage(file_field) -> bool:
    """
    Verifica se o campo usa o FileSystemStorage padrão do Django.
    Campos com storage customizado (S3, PrivateMediaStorage, etc.)
    devem usar storage.delete() em vez de os.remove().
    """
    from django.core.files.storage import default_storage
    return type(file_field.storage) is type(default_storage)


def delete_old_file(instance: models.Model, field_name: str) -> None:
    """
    Remove arquivo antigo quando o campo é substituído.

    Compatível com qualquer storage (filesystem local OU customizado
    como PrivateMediaStorage, S3, etc.).

    Args:
        instance: instância do model (já com o novo arquivo atribuído).
        field_name: nome do campo FileField/ImageField.
    """
    if not instance.pk:
        return

    try:
        model_class  = instance.__class__
        old_instance = model_class.objects.get(pk=instance.pk)
        old_file     = getattr(old_instance, field_name, None)
        new_file     = getattr(instance, field_name, None)

        if not old_file or old_file == new_file:
            return

        # ── Storage customizado (PrivateMediaStorage, S3, etc.) ──────────────
        if not _file_uses_default_storage(old_file):
            old_file.storage.delete(old_file.name)
            logger.debug(
                "Arquivo antigo removido via storage customizado: %s (campo %s, pk=%s)",
                old_file.name, field_name, instance.pk,
            )
            return

        # ── FileSystem local padrão ───────────────────────────────────────────
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)
            logger.debug(
                "Arquivo antigo removido: %s (campo %s, pk=%s)",
                old_file.path, field_name, instance.pk,
            )

    except model_class.DoesNotExist:
        pass
    except Exception:
        logger.warning(
            "delete_old_file: falha ao remover arquivo antigo (campo %s, pk=%s)",
            field_name, instance.pk,
            exc_info=True,
        )


def safe_delete_file(instance: models.Model, field_name: str) -> None:
    """
    Remove arquivo físico ao excluir o registro.

    Compatível com qualquer storage (filesystem local OU customizado
    como PrivateMediaStorage, S3, etc.).

    Args:
        instance: instância do model sendo excluída.
        field_name: nome do campo FileField/ImageField.
    """
    try:
        file_field = getattr(instance, field_name, None)
        if not file_field or not file_field.name:
            return

        # ── Storage customizado ───────────────────────────────────────────────
        if not _file_uses_default_storage(file_field):
            file_field.storage.delete(file_field.name)
            logger.debug(
                "Arquivo removido via storage customizado na exclusão: %s (campo %s, pk=%s)",
                file_field.name, field_name, getattr(instance, "pk", "?"),
            )
            return

        # ── FileSystem local padrão ───────────────────────────────────────────
        if os.path.isfile(file_field.path):
            os.remove(file_field.path)
            logger.debug(
                "Arquivo removido na exclusão: %s (campo %s, pk=%s)",
                file_field.path, field_name, getattr(instance, "pk", "?"),
            )

    except Exception:
        logger.warning(
            "safe_delete_file: falha ao remover arquivo (campo %s, pk=%s)",
            field_name, getattr(instance, "pk", "?"),
            exc_info=True,
        )

