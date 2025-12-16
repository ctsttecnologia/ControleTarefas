
# chat/validators.py
import os
from django.core.exceptions import ValidationError

# Tenta importar magic, mas não falha se não estiver disponível
try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    MAGIC_AVAILABLE = False

ALLOWED_MIME_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/webp': ['.webp'],
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'text/plain': ['.txt'],
    'application/zip': ['.zip'],
    'application/x-rar-compressed': ['.rar'],
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_uploaded_file(file):
    """Valida arquivo enviado com verificação real do conteúdo"""
    errors = []
    
    # 1. Verifica tamanho
    if file.size > MAX_FILE_SIZE:
        errors.append(f"Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # 2. Verifica extensão
    ext = os.path.splitext(file.name)[1].lower()
    valid_extensions = []
    for exts in ALLOWED_MIME_TYPES.values():
        valid_extensions.extend(exts)
    
    if ext not in valid_extensions:
        errors.append(f"Extensão {ext} não permitida")
    
    # 3. Verifica MIME type real do arquivo (se magic estiver disponível)
    if MAGIC_AVAILABLE:
        try:
            file.seek(0)
            mime = magic.from_buffer(file.read(2048), mime=True)
            file.seek(0)
            
            if mime not in ALLOWED_MIME_TYPES:
                errors.append(f"Tipo de arquivo {mime} não permitido")
            
            # Verifica se extensão corresponde ao MIME type
            if ext not in ALLOWED_MIME_TYPES.get(mime, []):
                errors.append("Extensão não corresponde ao tipo de arquivo")
                
        except Exception as e:
            errors.append(f"Erro ao validar arquivo: {str(e)}")
    else:
        # Fallback: valida apenas pelo content_type do upload (menos seguro)
        content_type = getattr(file, 'content_type', None)
        if content_type and content_type not in ALLOWED_MIME_TYPES:
            errors.append(f"Tipo de arquivo {content_type} não permitido")
    
    if errors:
        raise ValidationError(errors)
    
    return True


