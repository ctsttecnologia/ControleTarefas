
# ferramentas/management/commands/expurgar_tokens_expirados.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import TokenAssinaturaRemota

class Command(BaseCommand):
    help = "Remove tokens de assinatura remota expirados há mais de 30 dias."

    def handle(self, *args, **options):
        limite = timezone.now() - timezone.timedelta(days=30)
        qs = TokenAssinaturaRemota.objects.filter(expira_em__lt=limite)
        count = qs.count()
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"{count} tokens expirados removidos."))
