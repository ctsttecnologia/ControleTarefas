
import base64
from django.conf import settings
from django.contrib.staticfiles import finders

def get_logo_base64():
    """
    Encontra o arquivo da logo nos diretórios estáticos,
    lê e o codifica em Base64 para ser embutido no HTML/PDF.
    """
    # IMPORTANTE: Altere 'images/logo.png' para o caminho correto da sua logo
    # dentro da pasta 'static'.
    logo_path = finders.find('images/logocetest.png')
    if not logo_path:
        return None
    
    with open(logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:image/png;base64,{encoded_string}"
