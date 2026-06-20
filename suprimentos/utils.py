
# suprimentos/utils.py
import logging

logger = logging.getLogger(__name__)


def _registrar_historico(func, **kwargs):
    """Wrapper seguro para registro de histórico — nunca quebra o fluxo."""
    try:
        func(**kwargs)
    except Exception:
        logger.exception("Falha ao registrar histórico (%s)", func.__qualname__)

