
# notifications/management/commands/gerar_notificacoes.py

"""
Management command para gerar notificações periódicas.
Executar diariamente via cron ou Celery Beat:
    python manage.py gerar_notificacoes
"""

from datetime import timedelta, date

from django.core.management.base import BaseCommand
from django.utils import timezone

from tarefas.models import Tarefas
from notifications.services import (
    notificar_tarefa_atrasada,
    notificar_tarefa_lembrete,
    notificar_tarefa_prazo_proximo,
    notificar_pgr_vencimento,
    notificar_pgr_plano_atrasado,
)


class Command(BaseCommand):
    help = 'Gera notificações para tarefas atrasadas, lembretes, PGR vencendo, etc.'

    def handle(self, *args, **options):
        now = timezone.now()
        hoje = date.today()
        total = 0

        self.stdout.write(self.style.NOTICE('🔔 Gerando notificações...'))

        # -----------------------------------------------------------------
        # 1. TAREFAS ATRASADAS
        # -----------------------------------------------------------------
        tarefas_atrasadas = Tarefas.objects.filter(
            prazo__lt=now,
        ).exclude(
            status__in=['concluida', 'cancelada'],
        ).select_related('responsavel')

        for tarefa in tarefas_atrasadas:
            resultado = notificar_tarefa_atrasada(tarefa)
            if resultado:
                total += 1

        # -----------------------------------------------------------------
        # 2. LEMBRETES (data_lembrete = hoje)
        # -----------------------------------------------------------------
        tarefas_lembrete = Tarefas.objects.filter(
            data_lembrete__date=hoje,
        ).exclude(
            status__in=['concluida', 'cancelada'],
        ).select_related('responsavel')

        for tarefa in tarefas_lembrete:
            resultado = notificar_tarefa_lembrete(tarefa)
            if resultado:
                total += 1

        # -----------------------------------------------------------------
        # 3. PRAZO NAS PRÓXIMAS 24h (mas não atrasadas)
        # -----------------------------------------------------------------
        tarefas_proximas = Tarefas.objects.filter(
            prazo__gte=now,
            prazo__lte=now + timedelta(days=1),
        ).exclude(
            status__in=['concluida', 'cancelada'],
        ).select_related('responsavel')

        for tarefa in tarefas_proximas:
            resultado = notificar_tarefa_prazo_proximo(tarefa)
            if resultado:
                total += 1

        # -----------------------------------------------------------------
        # 4. PGR PRÓXIMOS AO VENCIMENTO (30 e 15 dias)
        # -----------------------------------------------------------------
        try:
            from pgr_gestao.models import PGRDocumento

            pgrs_vencendo = PGRDocumento.objects.filter(
                data_vencimento__lte=hoje + timedelta(days=30),
                data_vencimento__gt=hoje,
                status='vigente',
            )

            for pgr in pgrs_vencendo:
                dias = (pgr.data_vencimento - hoje).days
                # Notifica o criador/responsável - ajustar conforme seu model
                if hasattr(pgr, 'criado_por') and pgr.criado_por:
                    resultado = notificar_pgr_vencimento(pgr, pgr.criado_por, dias)
                    if resultado:
                        total += 1

        except ImportError:
            self.stdout.write(self.style.WARNING('⚠️  App pgr_gestao não encontrada, pulando.'))

        # -----------------------------------------------------------------
        # 5. PLANOS DE AÇÃO ATRASADOS (PGR)
        # -----------------------------------------------------------------
        try:
            from pgr_gestao.models import PlanoAcaoPGR

            planos_atrasados = PlanoAcaoPGR.objects.filter(
                status__in=['pendente', 'em_andamento'],
                data_prevista__lt=hoje,
            ).select_related(
                'risco_identificado__pgr_documento'
            )

            for plano in planos_atrasados:
                if hasattr(plano, 'criado_por') and plano.criado_por:
                    resultado = notificar_pgr_plano_atrasado(plano, plano.criado_por)
                    if resultado:
                        total += 1

        except ImportError:
            pass

        self.stdout.write(self.style.SUCCESS(
            f'✅ {total} notificações criadas com sucesso!'
        ))

