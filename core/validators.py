import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, EmailValidator
from django.utils.translation import gettext_lazy as _
import os
from django.conf import settings
from core.magic_utils import get_mime_type

# =============================================================================
# == VALIDADORES DE DOCUMENTOS BRASILEIROS
# =============================================================================

def validate_cpf(value):
    cpf = ''.join(re.findall(r'\d', str(value)))
    if not cpf or len(cpf) != 11:
        raise ValidationError("CPF deve conter 11 dígitos.", code='invalid_cpf')
    if cpf in [s * 11 for s in "0123456789"]:
        raise ValidationError("CPF inválido (todos os dígitos são iguais).", code='invalid_cpf')
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = 11 - (soma % 11)
    digito_verificador_1 = resto if resto < 10 else 0
    if digito_verificador_1 != int(cpf[9]):
        raise ValidationError("CPF inválido (dígito verificador 1 incorreto).", code='invalid_cpf')
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = 11 - (soma % 11)
    digito_verificador_2 = resto if resto < 10 else 0
    if digito_verificador_2 != int(cpf[10]):
        raise ValidationError("CPF inválido (dígito verificador 2 incorreto).", code='invalid_cpf')


def validate_pis(value):
    pis = ''.join(re.findall(r'\d', str(value)))
    if not pis or len(pis) != 11:
        raise ValidationError("PIS/PASEP/NIT deve conter 11 dígitos.", code='invalid_pis')
    pesos = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(pis[i]) * pesos[i] for i in range(10))
    resto = soma % 11
    digito_verificador = 0 if resto < 2 else 11 - resto
    if digito_verificador != int(pis[10]):
        raise ValidationError("PIS/PASEP/NIT inválido (dígito verificador incorreto).", code='invalid_pis')


def validate_cnpj(value):
    cnpj = ''.join(re.findall(r'\d', str(value)))
    if not cnpj or len(cnpj) != 14:
        raise ValidationError("CNPJ deve conter 14 dígitos.", code='invalid_cnpj')
    if cnpj in [s * 14 for s in "0123456789"]:
        raise ValidationError("CNPJ inválido (todos os dígitos são iguais).", code='invalid_cnpj')
    pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos_1[i] for i in range(12))
    resto = soma % 11
    digito_verificador_1 = 0 if resto < 2 else 11 - resto
    if digito_verificador_1 != int(cnpj[12]):
        raise ValidationError("CNPJ inválido (dígito verificador 1 incorreto).", code='invalid_cnpj')
    pesos_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos_2[i] for i in range(13))
    resto = soma % 11
    digito_verificador_2 = 0 if resto < 2 else 11 - resto
    if digito_verificador_2 != int(cnpj[13]):
        raise ValidationError("CNPJ inválido (dígito verificador 2 incorreto).", code='invalid_cnpj')


# =============================================================================
# == VALIDADORES DE CONTATO
# =============================================================================

validate_telefone = RegexValidator(
    regex=r'^\(\d{2}\) \d{4,5}-\d{4}$',
    message=_("O número de telefone deve estar no formato (00) 0000-0000 ou (00) 00000-0000.")
)

validate_email = EmailValidator(
    message=_('Informe um endereço de e-mail válido.')
)

# ============================================================
#  VALIDADORES DE UPLOAD SEGURO
# ============================================================

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


def _extensions_to_allowed_types(extensions):
    """Converte lista de extensões ['jpg', 'pdf'] → {'image/jpeg': ['.jpg'], ...}"""
    allowed = {}
    for ext in extensions:
        dot_ext = f'.{ext}' if not ext.startswith('.') else ext
        dot_ext = dot_ext.lower()
        mime = _EXT_TO_MIME.get(dot_ext)
        if mime:
            allowed.setdefault(mime, [])
            if dot_ext not in allowed[mime]:
                allowed[mime].append(dot_ext)
    return allowed


def get_upload_config(app_name):
    """
    Retorna a config de upload para o app especificado.
    Busca primeiro em UPLOAD_CONFIG, depois em UPLOAD_CATEGORIES (convertendo).
    """
    upload_config = getattr(settings, 'UPLOAD_CONFIG', {})
    if app_name in upload_config:
        return upload_config[app_name]

    upload_categories = getattr(settings, 'UPLOAD_CATEGORIES', {})
    if app_name in upload_categories:
        cat = upload_categories[app_name]
        return {
            'max_size_mb': cat.get('max_size_mb', 10),
            'allowed_types': _extensions_to_allowed_types(cat.get('extensions', [])),
        }

    if 'default' in upload_config:
        return upload_config['default']

    return {
        'max_size_mb': 10,
        'allowed_types': {
            'application/pdf': ['.pdf'],
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
        },
    }


class SecureFileValidator:
    """
    Validator de upload configurável por app.
    Compatível com UPLOAD_CONFIG (allowed_types) e UPLOAD_CATEGORIES (extensions).

    Uso:
        file = models.FileField(validators=[SecureFileValidator('suprimentos_solicitacao')])
    """

    def __init__(self, app_name='default'):
        self.app_name = app_name

    def __call__(self, file):
        self.config = get_upload_config(self.app_name)
        self._validate_filename(file)
        self._validate_extension(file)
        self._validate_mime_type(file)
        self._validate_size(file)
        self._validate_mime_extension_match(file)
        if self._is_image(file):
            self._validate_image_integrity(file)

    # ── Helpers internos (conversão de formato) ──────────────

    def _get_allowed_types(self):
        """Retorna dict {mime: ['.ext', ...]} independente do formato."""
        if 'allowed_types' in self.config:
            return self.config['allowed_types'] 
        if 'extensions' in self.config:
            return _extensions_to_allowed_types(self.config['extensions'])
        return {
            'application/pdf': ['.pdf'],
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
        }

    def _get_allowed_extensions(self):
        """Retorna lista plana de extensões permitidas."""
        allowed_types = self._get_allowed_types()
        exts = []
        for ext_list in allowed_types.values():
            exts.extend(ext_list)
        return list(set(exts))

    def _get_max_size_mb(self):
        return self.config.get('max_size_mb', 10)

    # ── Validações ───────────────────────────────────────────

    def _validate_filename(self, file):
        name = os.path.basename(file.name)
        dangerous = ['..', '/', '\\', '\x00', '<', '>', '|', ':', '"']
        if any(char in name for char in dangerous):
            raise ValidationError(
                'Nome de arquivo contém caracteres inválidos.',
                code='invalid_filename',
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
                f'Extensão "{ext}" não permitida em {self.app_name}. '
                f'Aceitas: {", ".join(sorted(allowed))}',
                code='invalid_extension',
            )

    def _validate_mime_type(self, file):
        mime = self._read_mime(file)
        allowed_mimes = list(self._get_allowed_types().keys())
        if mime not in allowed_mimes:
            raise ValidationError(
                f'Tipo de arquivo "{mime}" não permitido em {self.app_name}. '
                f'Aceitos: {", ".join(allowed_mimes)}',
                code='invalid_mime',
            )

    def _validate_size(self, file):
        max_mb = self._get_max_size_mb()
        max_bytes = max_mb * 1024 * 1024
        if file.size > max_bytes:
            size_mb = file.size / (1024 * 1024)
            raise ValidationError(
                f'Arquivo muito grande ({size_mb:.1f}MB). '
                f'Máximo para {self.app_name}: {max_mb}MB.',
                code='file_too_large',
            )

    def _validate_mime_extension_match(self, file):
        mime = self._read_mime(file)
        ext = os.path.splitext(file.name)[1].lower()
        expected_exts = self._get_allowed_types().get(mime, [])
        if expected_exts and ext not in expected_exts:
            raise ValidationError(
                f'A extensão "{ext}" não corresponde ao conteúdo real ({mime}). '
                f'Possível tentativa de disfarçar o tipo do arquivo.',
                code='mime_mismatch',
            )

    def _validate_image_integrity(self, file):
        from PIL import Image
        try:
            file.seek(0)
            img = Image.open(file)
            img.verify()
            file.seek(0)
        except Exception:
            raise ValidationError(
                'Imagem corrompida ou inválida.',
                code='corrupt_image',
            )

    # ── Outros helpers ───────────────────────────────────────

    def _read_mime(self, file):
        return get_mime_type(file)

    def _is_image(self, file):
        return self._read_mime(file).startswith('image/')

    def deconstruct(self):
        return (
            f'{self.__class__.__module__}.{self.__class__.__qualname__}',
            [],
            {'app_name': self.app_name},
        )

    def __eq__(self, other):
        return isinstance(other, SecureFileValidator) and self.app_name == other.app_name


class SecureImageValidator(SecureFileValidator):
    """
    Validator específico para campos ImageField.
    Herda toda a lógica do SecureFileValidator mas
    sempre valida integridade de imagem.
    """

    def __call__(self, file):
        self.config = get_upload_config(self.app_name)
        self._validate_filename(file)
        self._validate_extension(file)
        self._validate_mime_type(file)
        self._validate_size(file)
        self._validate_mime_extension_match(file)
        self._validate_image_integrity(file)

    def deconstruct(self):
        return (
            f'{self.__class__.__module__}.{self.__class__.__qualname__}',
            [],
            {'app_name': self.app_name},
        )

    def __eq__(self, other):
        return isinstance(other, SecureImageValidator) and self.app_name == other.app_name

    