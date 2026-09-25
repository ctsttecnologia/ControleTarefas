
# seguranca_trabalho/management/commands/anonimizar_dados_sensiveis_sst.py
"""
Comando de retenção/anonimização de dados sensíveis do módulo SST,
em conformidade com LGPD (art. 16) e NR-6/CLT.

Regra:
- Mantém o REGISTRO de entrega/ficha (exigência legal por até 20 anos).
- Anonimiza apenas o dado sensível (assinatura) após N anos do
  desligamento do funcionário, pois a imagem/base64 da assinatura
  não é, por si, exigência legal de guarda de longo prazo.

Uso:
    python manage.py anonimizar_dados_sensiveis_sst
    python manage.py anonimizar_dados_sensiveis_sst --anos 5
    python manage.py anonimizar_dados_sensiveis_sst --dry-run
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from departamento_pessoal.models import Funcionario
from seguranca_trabalho.models import FichaEPI, EntregaEPI

# Ajuste conforme política interna (recomendação: 5 anos após desligamento,
# respeitando prescrição trabalhista de 2 anos + bienal + margem de segurança).
PRAZO_ANONIMIZACAO_ANOS = 5


class Command(BaseCommand):
    help = (
        "Anonimiza assinaturas de fichas/entregas de EPI de funcionários "
        "desligados há mais de N anos (padrão: 5), mantendo o registro "
        "histórico exigido por NR-6/CLT."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--anos', type=int, default=PRAZO_ANONIMIZACAO_ANOS,
            help="Anos após o desligamento para anonimizar dados sensíveis."
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Apenas simula, sem gravar alterações."
        )

    def handle(self, *args, **options):
        anos = options['anos']
        dry_run = options['dry_run']
        limite = timezone.now().date() - timedelta(days=365 * anos)

        funcionarios_elegiveis = Funcionario.objects.filter(
            status='INATIVO',
            data_demissao__isnull=False,
            data_demissao__lte=limite,
        )

        total_fichas = 0
        total_entregas = 0

        self.stdout.write(
            f"Buscando funcionários desligados até {limite} "
            f"({'DRY-RUN' if dry_run else 'EXECUÇÃO REAL'})..."
        )

        with transaction.atomic():
            fichas = FichaEPI.objects.filter(
                funcionario__in=funcionarios_elegiveis,
                assinatura_funcionario__isnull=False,   # só isnull funciona
            )

            for ficha in fichas:
                if not ficha.assinatura_funcionario:   # filtra '' em Python
                    continue
                if not dry_run:
                    ficha.assinatura_funcionario = None
                    ficha.data_assinatura_termo = None
                    ficha.save(update_fields=[
                        'assinatura_funcionario', 'data_assinatura_termo'
                    ])
                total_fichas += 1

            entregas = EntregaEPI.objects.filter(
                ficha__funcionario__in=funcionarios_elegiveis,
                assinatura_recebimento__isnull=False,
            )

            for entrega in entregas:
                if not entrega.assinatura_recebimento:
                    continue
                if not dry_run:
                    entrega.assinatura_recebimento = None
                    entrega.save(update_fields=['assinatura_recebimento'])
                total_entregas += 1
