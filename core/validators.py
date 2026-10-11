import logging
import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, RegexValidator
from django.utils.translation import gettext_lazy as _

from core.magic_utils import get_mime_type

logger = logging.getLogger(__name__)


# =============================================================================
# == DOCUMENTOS BRASILEIROS
# =============================================================================

def _so_digitos(value) -> str:
    return re.sub(r'\D', '', str(value or ''))


def validate_cpf(value):
    cpf = _so_digitos(value)
    if len(cpf) != 11:
        raise ValidationError("CPF deve conter 11 dígitos.", code='invalid_cpf')
    if len(set(cpf)) == 1:
        raise ValidationError("CPF inválido (todos os dígitos são iguais).", code='invalid_cpf')

    for n in (9, 10):
        soma = sum(int(cpf[i]) * (n + 1 - i) for i in range(n))
        resto = 11 - (soma % 11)
        dv = resto if resto < 10 else 0
        if dv != int(cpf[n]):
            raise ValidationError(
                f"CPF inválido (dígito verificador {n - 8} incorreto).", code='invalid_cpf'
            )


def validate_pis(value):
    pis = _so_digitos(value)
    if len(pis) != 11:
        raise ValidationError("PIS/PASEP/NIT deve conter 11 dígitos.", code='invalid_pis')
    pesos = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    resto = sum(int(pis[i]) * pesos[i] for i in range(10)) % 11
    dv = 0 if resto < 2 else 11 - resto
    if dv != int(pis[10]):
        raise ValidationError(
            "PIS/PASEP/NIT inválido (dígito verificador incorreto).", code='invalid_pis'
        )


_PESOS_CNPJ = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def _cnpj_dv(base: str) -> int:
    """Módulo 11 com valor = ord(char) - 48 (compatível com CNPJ numérico e alfanumérico)."""
    pesos = _PESOS_CNPJ[-len(base):]
    resto = sum((ord(c) - 48) * p for c, p in zip(base, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def validate_cnpj(value):
    """Aceita CNPJ numérico e alfanumérico (12 posições alfanuméricas + 2 dígitos)."""
    cnpj = re.sub(r'[^0-9A-Za-z]', '', str(value or '')).upper()
    if not re.fullmatch(r'[0-9A-Z]{12}\d{2}', cnpj):
        raise ValidationError(
            "CNPJ deve conter 14 caracteres (12 alfanuméricos + 2 dígitos).",
            code='invalid_cnpj',
        )
    if len(set(cnpj)) == 1:
        raise ValidationError(
            "CNPJ inválido (todos os caracteres são iguais).", code='invalid_cnpj'
        )
    if _cnpj_dv(cnpj[:12]) != int(cnpj[12]):
        raise ValidationError(
            "CNPJ inválido (dígito verificador 1 incorreto).", code='invalid_cnpj'
        )
    if _cnpj_dv(cnpj[:13]) != int(cnpj[13]):
        raise ValidationError(
            "CNPJ inválido (dígito verificador 2 incorreto).", code='invalid_cnpj'
        )


# =============================================================================
# == CONTATO
# =============================================================================

validate_telefone = RegexValidator(
    regex=r'^\(\d{2}\) \d{4,5}-\d{4}$',
    message=_("O número de telefone deve estar no formato (00) 0000-0000 ou (00) 00000-0000."),
)

validate_email = EmailValidator(message=_('Informe um endereço de e-mail válido.'))


# =============================================================================
# == UPLOAD SEGURO
# =============================================================================

_EXT_TO_MIME = {
    '.pdf':  'application/pdf',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png':  'image/png',
    '.webp': 'image/webp',
    '.gif':  'image/gif',
    '.bmp':  'image/bmp',
    '.doc':  'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls':  'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.csv':  'text/csv',
    '.txt':  'text/plain',
    '.zip':  'application/zip',
    '.rar':  'application/x-rar-compressed',
    '.mp4':  'video/mp4',
    '.mp3':  'audio/mpeg',
}

# MIMEs que o libmagic costuma devolver para formatos Office/CSV.
# Só são aceitos quando a extensão declarada corresponde ao MIME esperado.
_MIME_COMPAT = {
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
        'application/zip', 'application/octet-stream',
    },
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {
        'application/zip', 'application/octet-stream',
    },
    'application/msword': {
        'application/CDFV2', 'application/x-ole-storage', 'application/vnd.ms-office',
        'application/octet-stream',
    },
    'application/vnd.ms-excel': {
        'application/CDFV2', 'application/x-ole-storage', 'application/vnd.ms-office',
        'application/octet-stream',
    },
    'text/csv': {'text/plain', 'application/csv'},
    'image/jpeg': {'image/jpg', 'image/pjpeg'},
}

_DEFAULT_CONFIG = {
    'max_size_mb': 10,
    'allowed_types': {
        'application/pdf': ['.pdf'],
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
    },
}


def _extensions_to_allowed_types(extensions):
    """['jpg', 'pdf'] → {'image/jpeg': ['.jpg'], 'application/pdf': ['.pdf']}"""
    allowed = {}
    for ext in extensions:
        dot_ext = (ext if ext.startswith('.') else f'.{ext}').lower()
        mime = _EXT_TO_MIME.get(dot_ext)
        if not mime:
            logger.warning("Extensão %s sem MIME em _EXT_TO_MIME; ignorada.", dot_ext)
            continue
        lst = allowed.setdefault(mime, [])
        if dot_ext not in lst:
            lst.append(dot_ext)
    return allowed


def get_upload_config(app_name):
    """Busca em UPLOAD_CONFIG, depois em UPLOAD_CATEGORIES, depois no default."""
    upload_config = getattr(settings, 'UPLOAD_CONFIG', {})
    if app_name in upload_config:
        return upload_config[app_name]

    categories = getattr(settings, 'UPLOAD_CATEGORIES', {})
    if app_name in categories:
        cat = categories[app_name]
        return {
            'max_size_mb': cat.get('max_size_mb', 10),
            'allowed_types': _extensions_to_allowed_types(cat.get('extensions', [])),
        }

    logger.warning("Config de upload '%s' não encontrada; usando default.", app_name)
    return upload_config.get('default', _DEFAULT_CONFIG)


class SecureFileValidator:
    """
    Validator de upload configurável por app (UPLOAD_CONFIG / UPLOAD_CATEGORIES).

        file = models.FileField(max_length=255, validators=[SecureFileValidator('pgr_anexos')])

    Arquivos já salvos (FieldFile com _committed=True) não são revalidados.
    """

    force_image_check = False

    def __init__(self, app_name='default'):
        self.app_name = app_name

    @property
    def config(self):
        return get_upload_config(self.app_name)

    def __call__(self, file):
        if getattr(file, '_committed', False):
            return

        self._validate_filename(file)
        self._validate_extension(file)
        self._validate_size(file)               # barato: antes de ler o conteúdo

        detected = self._read_mime(file)        # lido uma única vez
        mime = self._normalize_mime(detected, file)
        self._validate_mime_type(mime)
        self._validate_mime_extension_match(mime, file)
        self._validate_office_container(file)

        if self.force_image_check or mime.startswith('image/'):
            self._validate_image_integrity(file)

    # ── Config ───────────────────────────────────────────────

    def _get_allowed_types(self):
        cfg = self.config
        if 'allowed_types' in cfg:
            return cfg['allowed_types']
        if 'extensions' in cfg:
            return _extensions_to_allowed_types(cfg['extensions'])
        return _DEFAULT_CONFIG['allowed_types']

    def _get_allowed_extensions(self):
        return {e for exts in self._get_allowed_types().values() for e in exts}

    def _get_max_size_mb(self):
        return self.config.get('max_size_mb', 10)

    # ── Validações ───────────────────────────────────────────

    def _validate_filename(self, file):
        name = os.path.basename(file.name or '')
        if not name:
            raise ValidationError('Arquivo sem nome.', code='invalid_filename')
        if any(c in name for c in ('..', '\\', '\x00', '<', '>', '|', ':', '"')):
            raise ValidationError(
                'Nome de arquivo contém caracteres inválidos.', code='invalid_filename'
            )
        if len(name) > 255:
            raise ValidationError(
                'Nome de arquivo muito longo (máximo: 255 caracteres).',
                code='filename_too_long',
            )

    def _validate_extension(self, file):
        ext = os.path.splitext(file.name)[1].lower()
        allowed = self._get_allowed_extensions()
        if ext not in allowed:
            raise ValidationError(
                f'Extensão "{ext}" não permitida. Aceitas: {", ".join(sorted(allowed))}',
                code='invalid_extension',
            )

    def _get_file_size(self, file):
        size = file.size
        if size is None:
            f = getattr(file, 'file', file)
            pos = f.tell()
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(pos)
        return size

    def _validate_size(self, file):
        try:
            size = self._get_file_size(file)
        except (FileNotFoundError, OSError, ValueError):
            return  # arquivo órfão / sem arquivo associado
        max_mb = self._get_max_size_mb()
        if size > max_mb * 1024 * 1024:
            raise ValidationError(
                f'Arquivo muito grande. Máximo permitido: {max_mb} MB.',
                code='file_too_large',
            )

    def _normalize_mime(self, detected, file):
        """Converte MIMEs genéricos (zip, CDFV2, text/plain) no MIME esperado pela extensão."""
        ext = os.path.splitext(file.name)[1].lower()
        expected = _EXT_TO_MIME.get(ext)
        if (
            expected
            and detected != expected
            and detected in _MIME_COMPAT.get(expected, ())
            and expected in self._get_allowed_types()
        ):
            return expected
        return detected

    def _validate_mime_type(self, mime):
        allowed = list(self._get_allowed_types())
        if mime not in allowed:
            raise ValidationError(
                f'Tipo de arquivo "{mime}" não permitido. Aceitos: {", ".join(allowed)}',
                code='invalid_mime',
            )

    def _validate_mime_extension_match(self, mime, file):
        ext = os.path.splitext(file.name)[1].lower()
        expected = self._get_allowed_types().get(mime, [])
        if expected and ext not in expected:
            raise ValidationError(
                f'A extensão "{ext}" não corresponde ao conteúdo real ({mime}). '
                f'Possível tentativa de disfarçar o tipo do arquivo.',
                code='mime_mismatch',
            )

    _OFFICE_ZIP_MARKER = {'.docx': 'word/', '.xlsx': 'xl/'}

    def _validate_office_container(self, file):
        """DOCX/XLSX são ZIPs: confere a estrutura interna em vez de aceitar qualquer ZIP."""
        import zipfile
        ext = os.path.splitext(file.name)[1].lower()
        marker = self._OFFICE_ZIP_MARKER.get(ext)
        if not marker:
            return
        try:
            file.seek(0)
            with zipfile.ZipFile(file) as zf:
                names = zf.namelist()
        except Exception:
            raise ValidationError('Arquivo Office corrompido ou inválido.', code='invalid_office')
        finally:
            self._rewind(file)
        if '[Content_Types].xml' not in names or not any(n.startswith(marker) for n in names):
            raise ValidationError(
                'O conteúdo do arquivo não corresponde a um documento Office válido.',
                code='invalid_office',
            )

    def _validate_image_integrity(self, file):
        from PIL import Image
        try:
            file.seek(0)
            Image.open(file).verify()
        except Exception:
            raise ValidationError('Imagem corrompida ou inválida.', code='corrupt_image')
        finally:
            self._rewind(file)

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _rewind(file):
        try:
            file.seek(0)
        except Exception:
            pass

    def _read_mime(self, file):
        try:
            return get_mime_type(file)
        except Exception:
            logger.exception("Falha ao detectar MIME de '%s'", getattr(file, 'name', ''))
            raise ValidationError(
                'Não foi possível verificar o tipo do arquivo.', code='mime_detection_failed'
            )
        finally:
            self._rewind(file)

    def deconstruct(self):
        return (
            f'{self.__class__.__module__}.{self.__class__.__qualname__}',
            [],
            {'app_name': self.app_name},
        )

    def __eq__(self, other):
        return type(self) is type(other) and self.app_name == other.app_name

    def __hash__(self):
        return hash((type(self).__name__, self.app_name))


class SecureImageValidator(SecureFileValidator):
    """Para ImageField: sempre valida a integridade da imagem."""
    force_image_check = True

    