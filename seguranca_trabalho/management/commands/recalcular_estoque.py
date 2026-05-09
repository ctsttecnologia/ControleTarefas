
# seguranca_trabalho/management/commands/recalcular_estoque.py
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum, Case, When, IntegerField, F
from django.db.models.functions import Coalesce

from seguranca_trabalho.models import Equipamento


class Command(BaseCommand):
    help = (
        "Recalcula Equipamento.estoque_atual a partir do somatório de "
        "MovimentacaoEstoque (ENTRADA - SAIDA). Útil para auditoria e reconciliação."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas exibe divergências, sem gravar alterações.',
        )
        parser.add_argument(
            '--equipamento',
            type=int,
            default=None,
            help='ID de um equipamento específico para reconciliar.',
        )
        parser.add_argument(
            '--verbose-list',
            action='store_true',
            help='Lista todos os equipamentos verificados, não só os divergentes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        eq_id = options['equipamento']
        verbose_list = options['verbose_list']

        qs = Equipamento.objects.all()
        if eq_id is not None:
            qs = qs.filter(pk=eq_id)
            if not qs.exists():
                raise CommandError(f"Equipamento id={eq_id} não encontrado.")

        # Saldo correto = SUM(CASE WHEN tipo='ENTRADA' THEN qtd
        #                           WHEN tipo='SAIDA'   THEN -qtd
        #                           ELSE 0 END)
        qs = qs.annotate(
            saldo_correto=Coalesce(
                Sum(
                    Case(
                        When(movimentacoes_estoque__tipo='ENTRADA',
                             then=F('movimentacoes_estoque__quantidade')),
                        When(movimentacoes_estoque__tipo='SAIDA',
                             then=-F('movimentacoes_estoque__quantidade')),
                        default=0,
                        output_field=IntegerField(),
                    )
                ),
                0,
            )
        ).only('id', 'nome', 'estoque_atual')

        divergentes = []
        verificados = 0

        with transaction.atomic():
            for eq in qs.iterator():
                verificados += 1
                atual = eq.estoque_atual
                correto = eq.saldo_correto

                if atual != correto:
                    divergentes.append((eq.pk, eq.nome, atual, correto))
                    if not dry_run:
                        Equipamento.objects.filter(pk=eq.pk).update(
                            estoque_atual=correto
                        )
                elif verbose_list:
                    self.stdout.write(
                        f"  OK  [{eq.pk}] {eq.nome}: estoque={atual}"
                    )

            if dry_run:
                transaction.set_rollback(True)

        # ----------------- Relatório -----------------
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\nRelatório de Reconciliação de Estoque"
        ))
        self.stdout.write(f"Equipamentos verificados : {verificados}")
        self.stdout.write(f"Divergências encontradas : {len(divergentes)}")
        self.stdout.write(f"Modo                     : {'DRY-RUN' if dry_run else 'APLICADO'}")

        if divergentes:
            self.stdout.write(self.style.WARNING("\nDivergências:"))
            self.stdout.write(
                f"  {'ID':>6}  {'NOME':<40}  {'ATUAL':>8}  {'CORRETO':>8}  {'DIFF':>6}"
            )
            for pk, nome, atual, correto in divergentes:
                diff = correto - atual
                self.stdout.write(
                    f"  {pk:>6}  {(nome or '')[:40]:<40}  {atual:>8}  {correto:>8}  {diff:>+6}"
                )

        if divergentes and not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"\n{len(divergentes)} equipamento(s) ajustado(s) com sucesso."
            ))
        elif divergentes and dry_run:
            self.stdout.write(self.style.NOTICE(
                "\nNenhuma alteração gravada (dry-run)."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("\nEstoque íntegro. Nada a ajustar."))

