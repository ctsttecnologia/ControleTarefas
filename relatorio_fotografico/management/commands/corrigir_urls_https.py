
# relatorio_fotografico/management/commands/corrigir_urls_https.py
from django.core.management.base import BaseCommand
from relatorio_fotografico.models import FotoRelatorio

class Command(BaseCommand):
    help = 'Corrige URLs http:// para https:// no Cloudinary'

    def handle(self, *args, **options):
        fotos = FotoRelatorio.objects.all()
        corrigidas = 0
        for foto in fotos:
            url_atual = str(foto.imagem)
            if url_atual.startswith('http://res.cloudinary.com'):
                # CloudinaryField armazena o public_id, não a URL completa geralmente,
                # mas se estiver salvando a URL crua, force a troca:
                foto.imagem = url_atual.replace('http://', 'https://', 1)
                foto.save(update_fields=['imagem'])
                corrigidas += 1
        self.stdout.write(self.style.SUCCESS(f'{corrigidas} fotos corrigidas.'))


# Rode com: python manage.py corrigir_urls_https

