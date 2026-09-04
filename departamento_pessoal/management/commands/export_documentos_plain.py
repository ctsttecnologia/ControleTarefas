
import json
from django.core.management.base import BaseCommand
from departamento_pessoal.models import Documento


class Command(BaseCommand):
    help = "Exporta os campos criptografados (numero) em texto puro para migração de chave."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="documentos_backup.json")

    def handle(self, *args, **options):
        output = options["output"]
        dados = []
        erros = 0

        for doc in Documento.objects.all():
            try:
                dados.append({
                    "pk": doc.pk,
                    "numero": doc.numero,
                })
            except Exception as e:
                erros += 1
                self.stderr.write(f"Erro no doc {doc.pk}: {e}")

        with open(output, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Exportados {len(dados)} documentos ({erros} com erro) para {output}"
        ))

