
# core/management/commands/limpar_emails.py
import os
from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Limpa e-mails salvos em desenvolvimento'

    def handle(self, *args, **kwargs):
        path = settings.EMAIL_FILE_PATH
        if os.path.exists(path):
            count = 0
            for f in os.listdir(path):
                os.remove(os.path.join(path, f))
                count += 1
            self.stdout.write(self.style.SUCCESS(f'✅ {count} e-mails removidos'))

# Para usar: python manage.py limpar_emails
# python manage.py limpar_emails

# Para limpar e-mails salvos em desenvolvimento vis Powershell, execute:
# Remove-Item -Path "sent_emails\*" -Force