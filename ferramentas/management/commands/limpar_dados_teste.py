
# ferramentas/management/commands/limpar_dados_teste.py

from django.core.management.base import BaseCommand
from django.db import transaction
from ferramentas.models import (
    Atividade, AssinaturaMovimentacao, Movimentacao,
    ItemTermo, TermoDeResponsabilidade,
    Ferramenta, MalaFerramentas
)


class Command(BaseCommand):
    help = "Apaga TODOS os dados de teste do app ferramentas (irreversível)."

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a exclusão.')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirm']:
            self.stderr.write(self.style.ERROR(
                "⚠️  Operação destrutiva. Rode com --confirm para executar."
            ))
            return

        modelos = [
            AssinaturaMovimentacao, Movimentacao, ItemTermo,
            TermoDeResponsabilidade, Atividade, Ferramenta, MalaFerramentas,
        ]
        for modelo in modelos:
            count, _ = modelo.objects.all().delete()
            self.stdout.write(f"{modelo.__name__}: {count} registros apagados.")

        self.stdout.write(self.style.SUCCESS("✅ Limpeza concluída."))

# python manage.py limpar_dados_teste --confirm