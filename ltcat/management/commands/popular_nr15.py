
# ltcat/management/commands/popular_nr15.py

from django.core.management.base import BaseCommand
from ltcat.models import TabelaRuidoNR15


class Command(BaseCommand):
    help = "Popula tabela de limites de ruído NR-15 Anexo 1"

    def handle(self, *args, **options):
        dados = [
            (85, "8 horas"), (86, "7 horas"), (87, "6 horas"),
            (88, "5 horas"), (89, "4 horas e 30 minutos"),
            (90, "4 horas"), (91, "3 horas e 30 minutos"),
            (92, "3 horas"), (93, "2 horas e 40 minutos"),
            (94, "2 horas e 15 minutos"), (95, "2 horas"),
            (96, "1 hora e 45 minutos"), (98, "1 hora e 15 minutos"),
            (100, "1 hora"), (102, "45 minutos"), (104, "35 minutos"),
            (105, "30 minutos"), (106, "25 minutos"), (108, "20 minutos"),
            (110, "15 minutos"), (112, "10 minutos"), (114, "8 minutos"),
            (115, "7 minutos"),
        ]

        for nivel, exposicao in dados:
            TabelaRuidoNR15.objects.update_or_create(
                nivel_ruido_db=nivel,
                defaults={"max_exposicao_diaria": exposicao}
            )

        self.stdout.write(self.style.SUCCESS(
            f"{len(dados)} registros NR-15 Anexo 1 populados com sucesso!"
        ))

