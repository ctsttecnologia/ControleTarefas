
# relatorio_fotografico/services/geocoding.py
import logging

import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"


def obter_endereco_por_coordenadas(lat, lng, timeout=5):
    """Reverse geocoding via Nominatim (OpenStreetMap). Retorna None em falha."""
    if lat is None or lng is None:
        return None
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"lat": str(lat), "lon": str(lng), "format": "json"},
            headers={"User-Agent": "cetest-relatorio-fotografico/1.1.0"},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("display_name") or None
    except Exception:
        logger.warning("Falha ao geocodificar (%s, %s)", lat, lng, exc_info=True)
        return None

