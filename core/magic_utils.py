import logging

logger = logging.getLogger(__name__)

_SIGNATURES = (
    (b'%PDF-', 'application/pdf'),
    (b'\xff\xd8\xff', 'image/jpeg'),
    (b'\x89PNG\r\n\x1a\n', 'image/png'),
    (b'GIF87a', 'image/gif'),
    (b'GIF89a', 'image/gif'),
    (b'PK\x03\x04', 'application/zip'),
    (b'PK\x05\x06', 'application/zip'),
    (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', 'application/CDFV2'),   # DOC/XLS
    (b'Rar!\x1a\x07', 'application/x-rar-compressed'),
    (b'ID3', 'audio/mpeg'),
)


def _read_header(file_or_bytes, buf_size):
    if isinstance(file_or_bytes, (bytes, bytearray)):
        return bytes(file_or_bytes[:buf_size])
    file_or_bytes.seek(0)
    try:
        return file_or_bytes.read(buf_size)
    finally:
        file_or_bytes.seek(0)


def _sniff(h):
    """Fallback sem libmagic: identifica pelos bytes iniciais (nunca pelo nome)."""
    for sig, mime in _SIGNATURES:
        if h.startswith(sig):
            return mime
    if h[:4] == b'RIFF' and h[8:12] == b'WEBP':
        return 'image/webp'
    if h[:2] == b'BM' and len(h) > 14 and h[6:10] == b'\x00\x00\x00\x00':
        return 'image/bmp'
    if h[4:8] == b'ftyp':
        return 'video/mp4'
    if h[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'):
        return 'audio/mpeg'
    if h and not any(b < 9 or 13 < b < 32 for b in h):
        return 'text/plain'
    return 'application/octet-stream'


def get_mime_type(file_or_bytes, buf_size=8192):
    """MIME real pelo conteúdo. Desconhecido => 'application/octet-stream' (o validador rejeita)."""
    header = _read_header(file_or_bytes, buf_size)
    try:
        import magic
    except ImportError:
        logger.warning("python-magic/libmagic indisponível; usando detecção por assinatura.")
        return _sniff(header)
    try:
        return magic.from_buffer(header, mime=True)
    except Exception:
        logger.exception("Falha no libmagic; usando detecção por assinatura.")
        return _sniff(header)

