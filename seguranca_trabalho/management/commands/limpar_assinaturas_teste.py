
# seguranca_trabalho/management/commands/limpar_assinaturas_teste.py
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Zera assinaturas corrompidas (dados de teste, sem valor de produção)."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE seguranca_trabalho_fichaepi SET assinatura_funcionario = NULL"
            )
            fichas = cursor.rowcount

            cursor.execute(
                "UPDATE seguranca_trabalho_entregaepi SET assinatura_recebimento = NULL"
            )
            entregas = cursor.rowcount

        self.stdout.write(self.style.SUCCESS(
            f"Limpo: {fichas} fichas e {entregas} entregas."
        ))
