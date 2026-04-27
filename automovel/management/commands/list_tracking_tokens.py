
# automovel/management/commands/list_tracking_tokens.py
"""
Lista os tokens de rastreamento dos agendamentos para entrega aos devices GPS.

Uso:
    python manage.py list_tracking_tokens                    # ativos (agendado/em_andamento)
    python manage.py list_tracking_tokens --all              # todos
    python manage.py list_tracking_tokens --csv > tokens.csv # exportar
    python manage.py list_tracking_tokens --rotate ID        # gerar novo token p/ agendamento
"""

import csv
import sys
from django.core.management.base import BaseCommand, CommandError
from automovel.models import Carro_agendamento


class Command(BaseCommand):
    help = "Lista/rotaciona tokens de rastreamento de agendamentos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all", action="store_true",
            help="Inclui agendamentos finalizados/cancelados.",
        )
        parser.add_argument(
            "--csv", action="store_true",
            help="Saída em formato CSV (para importar em planilha).",
        )
        parser.add_argument(
            "--rotate", type=int, metavar="ID",
            help="Rotaciona o token do agendamento com o ID informado.",
        )

    def handle(self, *args, **opts):
        if opts["rotate"]:
            self._rotate(opts["rotate"])
            return

        qs = Carro_agendamento.objects.select_related("carro", "filial")
        if not opts["all"]:
            qs = qs.filter(status__in=["agendado", "em_andamento"])
        qs = qs.order_by("-data_hora_agenda")

        if opts["csv"]:
            self._dump_csv(qs)
        else:
            self._dump_table(qs)

    def _rotate(self, pk: int):
        try:
            ag = Carro_agendamento.objects.get(pk=pk)
        except Carro_agendamento.DoesNotExist:
            raise CommandError(f"Agendamento #{pk} não encontrado.")
        old = str(ag.tracking_token)[:8]
        new = ag.rotate_tracking_token()
        self.stdout.write(self.style.SUCCESS(
            f"✓ Token rotacionado para agendamento #{pk} ({ag.carro.placa})\n"
            f"  Anterior: {old}...\n"
            f"  Novo:     {new}"
        ))

    def _dump_csv(self, qs):
        writer = csv.writer(sys.stdout)
        writer.writerow(["agendamento_id", "filial", "placa", "funcionario",
                         "status", "data_inicio", "tracking_token"])
        for ag in qs:
            writer.writerow([
                ag.id,
                ag.filial.nome if ag.filial else "",
                ag.carro.placa,
                ag.funcionario,
                ag.status,
                ag.data_hora_agenda.isoformat(),
                str(ag.tracking_token),
            ])

    def _dump_table(self, qs):
        if not qs.exists():
            self.stdout.write(self.style.WARNING("Nenhum agendamento encontrado."))
            return
        self.stdout.write(self.style.HTTP_INFO(
            f"\n{'ID':>5} | {'PLACA':<10} | {'STATUS':<14} | {'FUNCIONÁRIO':<25} | TOKEN"
        ))
        self.stdout.write("-" * 110)
        for ag in qs:
            self.stdout.write(
                f"{ag.id:>5} | {ag.carro.placa:<10} | {ag.status:<14} | "
                f"{ag.funcionario[:25]:<25} | {ag.tracking_token}"
            )
        self.stdout.write(f"\nTotal: {qs.count()} agendamento(s)\n")

