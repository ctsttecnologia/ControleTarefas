
# ferramentas/utils.py
import base64
from pathlib import Path
from django.conf import settings


def get_logo_base64():
    """Retorna a logo da CETEST em base64 (data URI) para uso em PDFs.
    
    Necessário porque geradores de PDF (WeasyPrint/xhtml2pdf) não têm
    acesso garantido ao servidor de estáticos — base64 embute a imagem
    diretamente no HTML, sem depender de STATIC_URL/base_url.
    """
    logo_path = Path(settings.BASE_DIR) / 'static' / 'images' / 'logo.png'
    if logo_path.exists():
        with open(logo_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
    return None

