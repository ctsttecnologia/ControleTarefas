
# verificar_documentos.py

"""
Verifica status de documentos e envia notificações.

Executa:
1. Atualiza status (VIGENTE → A_VENCER → VENCIDO) com base em data_vencimento
2. Notifica responsáveis em marcos específicos (30, 15, 7, 1 dias + vencido)

Agende via cron/task scheduler para rodar 1x por dia:
    python manage.py verificar_documentos
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from documentos.models import Documento
from notifications.services import (
    notificar_documento_a_vencer,
    notificar_documento_vencido,
)


# Marcos de notificação (em dias antes do vencimento)
MARCOS_NOTIFICACAO = [30, 15, 7, 3, 1]


class Command(BaseCommand):
    help = 'Atualiza status de documentos e notifica responsáveis sobre vencimento'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula a execução sem alterar nada no banco',
        )
        parser.add_argument(
            '--silent',
            action='store_true',
            help='Não envia notificações (apenas atualiza status)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        silent = options['silent']
        hoje = timezone.now().date()

        self.stdout.write(self.style.HTTP_INFO(
            f'\n🔍 Verificando documentos em {hoje.strftime("%d/%m/%Y")}...'
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  Modo DRY-RUN: nenhuma alteração será salva.\n'))

        stats = {
            'vencidos_atualizados': 0,
            'a_vencer_atualizados': 0,
            'vigentes_atualizados': 0,
            'notif_vencidos': 0,
            'notif_a_vencer': 0,
        }

        # ── 1. Documentos VENCIDOS ────────────────────────────────────────
        qs_vencidos = Documento.objects.filter(
            data_vencimento__lt=hoje,
            status__in=[
                Documento.StatusChoices.VIGENTE,
                Documento.StatusChoices.A_VENCER,
                Documento.StatusChoices.VENCIDO,  # 🆕 inclui já vencidos para re-notificar
            ],
        ).exclude(responsavel__isnull=True)

        for doc in qs_vencidos:
            dias_atraso = (hoje - doc.data_vencimento).days
            ja_vencido = doc.status == Documento.StatusChoices.VENCIDO

            self.stdout.write(f'  🚨 VENCIDO: {doc.nome} ({dias_atraso}d de atraso)')

            if not dry_run:
                if not ja_vencido:
                    doc.status = Documento.StatusChoices.VENCIDO
                    doc.save(update_fields=['status'])
                    stats['vencidos_atualizados'] += 1

                # Re-notifica: imediatamente + a cada 7 dias de atraso
                if not silent and (dias_atraso == 0 or dias_atraso % 7 == 0):
                    notificar_documento_vencido(doc)
                    stats['notif_vencidos'] += 1


        # ── 2. Documentos A VENCER (dentro da janela de aviso) ────────────
        qs_a_vencer = Documento.objects.filter(
            data_vencimento__gte=hoje,
            status__in=[
                Documento.StatusChoices.VIGENTE,
                Documento.StatusChoices.A_VENCER,
            ],
        ).exclude(responsavel__isnull=True)

        for doc in qs_a_vencer:
            dias_restantes = (doc.data_vencimento - hoje).days
            limite = doc.dias_aviso or 30

            # Atualiza para A_VENCER se dentro da janela de aviso
            if dias_restantes <= limite and doc.status != Documento.StatusChoices.A_VENCER:
                self.stdout.write(f'  ⚠️  A VENCER: {doc.nome} ({dias_restantes} dias)')
                if not dry_run:
                    doc.status = Documento.StatusChoices.A_VENCER
                    doc.save(update_fields=['status'])
                    stats['a_vencer_atualizados'] += 1

            # Volta para VIGENTE se fora da janela (ex.: data foi estendida)
            elif dias_restantes > limite and doc.status == Documento.StatusChoices.A_VENCER:
                if not dry_run:
                    doc.status = Documento.StatusChoices.VIGENTE
                    doc.save(update_fields=['status'])
                    stats['vigentes_atualizados'] += 1

            # Notifica em marcos específicos (30, 15, 7, 3, 1)
            if not silent and dias_restantes in MARCOS_NOTIFICACAO:
                self.stdout.write(f'     📬 Notificando: {doc.responsavel} ({dias_restantes}d)')
                if not dry_run:
                    notificar_documento_a_vencer(doc)
                    stats['notif_a_vencer'] += 1

        # ── Resumo ────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS('\n✅ Verificação concluída:'))
        self.stdout.write(f"   • Marcados como VENCIDO:  {stats['vencidos_atualizados']}")
        self.stdout.write(f"   • Marcados como A_VENCER: {stats['a_vencer_atualizados']}")
        self.stdout.write(f"   • Voltaram para VIGENTE:  {stats['vigentes_atualizados']}")
        self.stdout.write(f"   • Notificações vencidos:  {stats['notif_vencidos']}")
        self.stdout.write(f"   • Notificações a vencer:  {stats['notif_a_vencer']}\n")

