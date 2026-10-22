
from django.core.management.base import BaseCommand
from gestao_riscos.services import propor_inspecoes

class Command(BaseCommand):
    help = "Propõe inspeções na meia-vida dos EPIs."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"{propor_inspecoes()} novas inspeções propostas."))
