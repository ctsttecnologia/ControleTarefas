
# suprimentos/management/commands/gerar_solicitacoes_pendentes.py
from django.core.management.base import BaseCommand
from dns import transaction
from suprimentos.models import Pedido, SolicitacaoCompra
from suprimentos.signals import _gerar_solicitacoes_do_pedido


class Command(BaseCommand):
    help = 'Gera SolicitacaoCompra para pedidos APROVADOS que ainda não têm.'

    def handle(self, *args, **opts):
        pedidos = Pedido.objects.filter(
            status=Pedido.StatusChoices.APROVADO
        ).exclude(
            pk__in=SolicitacaoCompra.objects.values_list('pedido_id', flat=True)
        )

        total = pedidos.count()
        self.stdout.write(f"📋 Encontrados {total} pedidos pendentes...")

        sucesso, falhas = 0, 0
        for p in pedidos:
            try:
                with transaction.atomic():
                    _gerar_solicitacoes_do_pedido(p)
                self.stdout.write(f"  ✅ {p.numero}")
                sucesso += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ {p.numero}: {e}"))
                falhas += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Concluído! {sucesso} ok, {falhas} falhas."))


