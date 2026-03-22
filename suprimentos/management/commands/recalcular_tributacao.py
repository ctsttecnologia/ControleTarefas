
# suprimentos/management/commands/recalcular_tributacao.py

# ┌─────────────────────────────────────────────────────────────┐
# │  1. CADASTRO BASE (Tributação)                              │
# │     NCM → CFOP → CST → Grupo Tributário                     │
# │     (com alíquotas + flags recuperável por imposto)          │
# └───────────────────┬─────────────────────────────────────────┘
#                     │
# ┌───────────────────▼─────────────────────────────────────────┐
# │  2. VINCULAÇÃO (Suprimentos > Material)                     │
# │     Material.ncm = NCM                                       │
# │     Material.grupo_tributario = GrupoTributário              │
# │     (preview AJAX mostra alíquotas ao selecionar)            │
# └───────────────────┬─────────────────────────────────────────┘
#                     │
# ┌───────────────────▼─────────────────────────────────────────┐
# │  3. CÁLCULO AUTOMÁTICO (ao salvar ItemPedido)               │
# │     material.calcular_custo_compra(valor, qtd)               │
# │     → grava custo_real, total_creditos, total_impostos       │
# └───────────────────┬─────────────────────────────────────────┘
#                     │
# ┌───────────────────▼─────────────────────────────────────────┐
# │  4. VISUALIZAÇÃO                                            │
# │     • Pedido detail → painel completo de impostos por item   │
#│     • Dashboard → card consolidado de custos do mês          │
# │     • Alerta → materiais sem grupo tributário                │
# └───────────────────┬─────────────────────────────────────────┘
#                     │
# ┌───────────────────▼─────────────────────────────────────────┐
# │  5. RECEBIMENTO (signal existente)                          │
# │     Pedido RECEBIDO → recalcula tributação                   │
# │                     → entrada estoque (EPI/CONSUMO/FERR)     │
# └─────────────────────────────────────────────────────────────┘


from decimal import Decimal
from django.core.management.base import BaseCommand
from suprimentos.models import ItemPedido


class Command(BaseCommand):
    help = "Recalcula custo_real, total_creditos e total_impostos de todos os ItemPedido"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas simula, não salva',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        itens = ItemPedido.objects.select_related(
            'material', 'material__grupo_tributario'
        ).all()

        atualizados = 0
        sem_grupo = 0

        for item in itens:
            if not item.material.grupo_tributario:
                sem_grupo += 1
                continue

            calc = item.calcular_impostos()
            novo_custo = calc['custo_real']
            novo_creditos = calc['total_creditos']
            novo_impostos = calc['total_impostos']

            if (item.custo_real != novo_custo or
                    item.total_creditos != novo_creditos or
                    item.total_impostos != novo_impostos):

                if not dry_run:
                    ItemPedido.objects.filter(pk=item.pk).update(
                        custo_real=novo_custo,
                        total_creditos=novo_creditos,
                        total_impostos=novo_impostos,
                    )
                atualizados += 1

                self.stdout.write(
                    f"  {'[DRY]' if dry_run else '[OK]'} "
                    f"Item #{item.pk} ({item.material.descricao}): "
                    f"R$ {item.valor_total} → Custo R$ {novo_custo} "
                    f"(créditos R$ {novo_creditos})"
                )

        self.stdout.write(self.style.SUCCESS(
            f"\n{'[DRY RUN] ' if dry_run else ''}"
            f"Atualizados: {atualizados} | Sem grupo: {sem_grupo} | "
            f"Total: {itens.count()}"
        ))

