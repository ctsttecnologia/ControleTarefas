
from django.core.management.base import BaseCommand
from django.db import connection
from departamento_pessoal.models import Documento


class Command(BaseCommand):
    help = "Corrige registros com 'numero' em texto puro, aplicando criptografia com a chave atual."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, CONVERT(numero USING utf8) FROM departamento_pessoal_documento"
            )
            rows = cursor.fetchall()

        self.stdout.write(f"Encontrados {len(rows)} registros.")

        for doc_id, numero_plain in rows:
            self.stdout.write(f"ID {doc_id}: {numero_plain!r}")
            if not dry_run:
                Documento.objects.filter(pk=doc_id).update(numero=numero_plain)

        self.stdout.write(self.style.SUCCESS("Concluído."))

