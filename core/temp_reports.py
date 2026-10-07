

# core/temp_reports.py  (novo arquivo)

import tempfile
import time
import uuid
from pathlib import Path

from django.conf import settings

TTL_SECONDS = 15 * 60


def _base_dir() -> Path:
    # Fora do MEDIA_ROOT: nunca servido publicamente
    d = Path(getattr(
        settings, "PRIVATE_TMP_DIR",
        Path(tempfile.gettempdir()) / "app_relatorios_tmp",
    ))
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    return d


def _purge_expired():
    now = time.time()
    for f in _base_dir().glob("*.xlsx"):
        try:
            if now - f.stat().st_mtime > TTL_SECONDS:
                f.unlink(missing_ok=True)
        except OSError:
            pass


def save_report(content: bytes, user_id) -> str:
    """Salva o relatório e devolve um token opaco."""
    _purge_expired()
    token = uuid.uuid4().hex
    (_base_dir() / f"{int(user_id)}_{token}.xlsx").write_bytes(content)
    return token


def pop_report(token, user_id):
    """Lê e apaga o relatório. Retorna None se inválido, expirado ou de outro usuário."""
    if not token or not str(token).isalnum():
        return None
    path = _base_dir() / f"{int(user_id)}_{token}.xlsx"
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > TTL_SECONDS:
        path.unlink(missing_ok=True)
        return None
    data = path.read_bytes()
    path.unlink(missing_ok=True)
    return data
