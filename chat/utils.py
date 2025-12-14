
# chat/utils.py
import bleach
from django.utils.html import escape

ALLOWED_TAGS = ['b', 'i', 'u', 'a', 'br', 'p', 'span']
ALLOWED_ATTRIBUTES = {'a': ['href', 'target', 'rel']}

def sanitize_message(content):
    """Sanitiza conteúdo de mensagens para prevenir XSS"""
    if not content:
        return ''
    
    # Remove tags perigosas
    cleaned = bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    
    return cleaned

def validate_message_content(content):
    """Valida conteúdo da mensagem"""
    if not content or not isinstance(content, str):
        return False, "Mensagem inválida"
    
    if len(content) > 10000:
        return False, "Mensagem muito longa (máximo 10.000 caracteres)"
    
    if len(content.strip()) == 0:
        return False, "Mensagem vazia"
    
    return True, None

