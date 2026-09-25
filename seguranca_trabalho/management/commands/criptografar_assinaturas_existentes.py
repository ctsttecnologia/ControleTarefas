
# seguranca_trabalho/management/commands/criptografar_assinaturas_existentes.py
from django.core.management.base import BaseCommand
from django.db import transaction
from seguranca_trabalho.models import FichaEPI, EntregaEPI

class Command(BaseCommand):
    help = "Regrava assinaturas existentes para aplicar criptografia (rodar 1x após migration)."

    def handle(self, *args, **options):
        total_fichas = 0
        with transaction.atomic():
            for ficha in FichaEPI.objects.exclude(assinatura_funcionario__isnull=True).exclude(assinatura_funcionario=''):
                ficha.save(update_fields=['assinatura_funcionario'])
                total_fichas += 1

        total_entregas = 0
        with transaction.atomic():
            for entrega in EntregaEPI.objects.exclude(assinatura_recebimento__isnull=True).exclude(assinatura_recebimento=''):
                entrega.save(update_fields=['assinatura_recebimento'])
                total_entregas += 1

        self.stdout.write(self.style.SUCCESS(
            f"Concluído: {total_fichas} fichas e {total_entregas} entregas criptografadas."
        ))

