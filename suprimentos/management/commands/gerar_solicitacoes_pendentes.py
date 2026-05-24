
# suprimentos/management/commands/gerar_solicitacoes_pendentes.py
from django.core.management.base import BaseCommand
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
        
        self.stdout.write(f"📋 Encontrados {pedidos.count()} pedidos pendentes...")
        
        for p in pedidos:
            self.stdout.write(f"  → {p.numero}")
            _gerar_solicitacoes_do_pedido(p)
        
        self.stdout.write(self.style.SUCCESS("✅ Concluído!"))

