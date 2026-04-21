
# core/magic_utils.py

import platform


def get_mime_type(file_or_bytes, buf_size=2048):
    """
    Detecta o MIME type real de um arquivo.

    Args:
        file_or_bytes: arquivo (com .read/.seek) ou bytes
        buf_size: quantidade de bytes para análise

    Returns:
        str: MIME type (ex: 'application/pdf', 'image/jpeg')
    """
    try:
        import magic

        if isinstance(file_or_bytes, bytes):
            return magic.from_buffer(file_or_bytes, mime=True)

        # É um file-like object
        file_or_bytes.seek(0)
        header = file_or_bytes.read(buf_size)
        file_or_bytes.seek(0)
        return magic.from_buffer(header, mime=True)

    except ImportError:
        # Fallback: se nenhum python-magic estiver instalado
        return _fallback_mime(file_or_bytes)


def _fallback_mime(file_or_bytes):
    """
    Fallback usando mimetypes (stdlib) — menos preciso,
    mas funciona sem dependência externa.
    """
    import mimetypes

    if hasattr(file_or_bytes, 'name'):
        mime, _ = mimetypes.guess_type(file_or_bytes.name)
        return mime or 'application/octet-stream'

    return 'application/octet-stream'

