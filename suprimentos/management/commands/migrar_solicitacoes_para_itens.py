
# suprimentos/management/commands/migrar_solicitacoes_para_itens.py
from django.core.management.base import BaseCommand
from django.db import transaction

from suprimentos.models import Cotacao, ItemSolicitacao, PedidoCompra, SolicitacaoCompra


class Command(BaseCommand):
    help = "Migra SolicitacaoCompra do fluxo antigo (sem itens) para o modelo com ItemSolicitacao."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Apenas simula, não salva nada')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        qs = SolicitacaoCompra.objects.filter(
            itens__isnull=True
        ).select_related('pedido', 'fornecedor')
        total = qs.count()
        self.stdout.write(f"📋 {total} solicitações sem itens encontradas.")

        migradas, erros = 0, 0
        for sol in qs:
            try:
                with transaction.atomic():
                    self._migrar_uma(sol)
                    if dry_run:
                        transaction.set_rollback(True)
                self.stdout.write(f"  ✅ SolicitacaoCompra #{sol.pk} migrada")
                migradas += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ SolicitacaoCompra #{sol.pk}: {e}"))
                erros += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n{'[DRY RUN] ' if dry_run else ''}Migradas: {migradas} | Erros: {erros} | Total: {total}"
        ))

    def _migrar_uma(self, sol):
        pedido = sol.pedido
        if not pedido:
            raise ValueError("Sem pedido vinculado")

        for item_ped in pedido.itens.all():
            item_sol = ItemSolicitacao.objects.create(
                solicitacao=sol,
                item_pedido_origem=item_ped,
                material=item_ped.material,
                quantidade=item_ped.quantidade,
                valor_unitario_estimado=item_ped.valor_unitario,
            )

            if sol.fornecedor and sol.valor_pedido:
                Cotacao.objects.create(
                    item_solicitacao=item_sol,
                    fornecedor=sol.fornecedor,
                    valor_unitario=item_ped.valor_unitario,
                    observacoes="Cotação migrada do fluxo antigo",
                )

        if getattr(sol, "numero_pedido_sienge", None):
            PedidoCompra.objects.create(
                solicitacao=sol,
                fornecedor=sol.fornecedor,
                numero_pedido=sol.numero_pedido_sienge,
                status='EMITIDO',
                data_emissao=sol.data_criacao_pedido,
                filial=getattr(sol, "filial", None) or getattr(pedido, "filial", None),
            )

