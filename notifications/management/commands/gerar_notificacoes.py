
# notifications/management/commands/gerar_notificacoes.py

"""
Management command para gerar notificações periódicas.
Executar diariamente via Celery Beat:
    python manage.py gerar_notificacoes
"""

from datetime import timedelta, date

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from tarefas.models import Tarefas
from notifications.services import (
    criar_notificacao,
    notificar_tarefa_atrasada,
    notificar_tarefa_lembrete,
    notificar_tarefa_prazo_proximo,
    notificar_pgr_vencimento,
    notificar_pgr_plano_atrasado,
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Gera notificações para tarefas atrasadas, EPIs vencendo, PGR, etc.'

    def handle(self, *args, **options):
        now = timezone.now()
        hoje = date.today()
        total = 0

        self.stdout.write(self.style.NOTICE('🔔 Gerando notificações...'))

        # =================================================================
        # 1. TAREFAS ATRASADAS
        # =================================================================
        tarefas_atrasadas = Tarefas.objects.filter(
            prazo__lt=now,
        ).exclude(
            status__in=['concluida', 'cancelada'],
        ).select_related('responsavel')

        for tarefa in tarefas_atrasadas:
            resultado = notificar_tarefa_atrasada(tarefa)
            if resultado:
                total += 1

        # =================================================================
        # 2. LEMBRETES (data_lembrete = hoje)
        # =================================================================
        if hasattr(Tarefas, 'data_lembrete'):
            tarefas_lembrete = Tarefas.objects.filter(
                data_lembrete__date=hoje,
            ).exclude(
                status__in=['concluida', 'cancelada'],
            ).select_related('responsavel')

            for tarefa in tarefas_lembrete:
                resultado = notificar_tarefa_lembrete(tarefa)
                if resultado:
                    total += 1

        # =================================================================
        # 3. PRAZO NAS PRÓXIMAS 24h (mas não atrasadas)
        # =================================================================
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

        # =================================================================
        # 4. EPIs - VENCIMENTO DE USO (30 e 15 dias)
        # =================================================================
        total += self._verificar_epis_vencendo(hoje)

        # =================================================================
        # 5. EPIs - CA (Certificado de Aprovação) VENCENDO
        # =================================================================
        total += self._verificar_cas_vencendo(hoje)

        # =================================================================
        # 6. PGR PRÓXIMOS AO VENCIMENTO (30 e 15 dias)
        # =================================================================
        total += self._verificar_pgr_vencendo(hoje)

        # =================================================================
        # 7. PLANOS DE AÇÃO ATRASADOS (PGR)
        # =================================================================
        total += self._verificar_planos_atrasados(hoje)

        # =================================================================
        # 8. TREINAMENTOS VENCENDO
        # =================================================================
        total += self._verificar_treinamentos_vencendo(hoje)

        self.stdout.write(self.style.SUCCESS(
            f'✅ {total} notificações criadas com sucesso!'
        ))

    # -----------------------------------------------------------------
    # MÉTODOS AUXILIARES
    # -----------------------------------------------------------------

    def _get_admins_e_seguranca(self):
        """Retorna usuários admin ou do grupo 'Segurança do Trabalho'."""
        return User.objects.filter(
            is_active=True,
        ).filter(
            # Admin OU membro do grupo SST
            is_staff=True,
        ).distinct()

    def _verificar_epis_vencendo(self, hoje):
        """Verifica EPIs com vencimento de uso próximo (30 dias) ou vencidos."""
        count = 0
        try:
            from seguranca_trabalho.models import EntregaEPI

            entregas = EntregaEPI.objects.select_related(
                'equipamento', 'ficha__funcionario'
            ).all()

            admins = list(self._get_admins_e_seguranca())

            for entrega in entregas:
                vencimento = entrega.data_vencimento_uso
                if not vencimento or not isinstance(vencimento, date):
                    continue

                dias_restantes = (vencimento - hoje).days
                funcionario = (
                    entrega.ficha.funcionario.nome_completo
                    if entrega.ficha and entrega.ficha.funcionario
                    else 'N/A'
                )
                epi_nome = entrega.equipamento.nome[:40]

                # EPI já vencido
                if dias_restantes < 0:
                    for admin in admins:
                        n = criar_notificacao(
                            usuario=admin,
                            titulo=f'EPI vencido: {epi_nome}',
                            tipo='sistema',
                            categoria='sistema',
                            prioridade='critica',
                            mensagem=(
                                f'{funcionario} - {epi_nome} '
                                f'venceu em {vencimento.strftime("%d/%m/%Y")} '
                                f'({abs(dias_restantes)} dias atrás).'
                            ),
                            url_destino=f'/seguranca/ficha/{entrega.ficha.pk}/'
                            if entrega.ficha else None,
                            icone='bi-shield-x',
                        )
                        if n:
                            count += 1

                # EPI vencendo em até 30 dias
                elif dias_restantes <= 30:
                    prioridade = 'critica' if dias_restantes <= 7 else (
                        'alta' if dias_restantes <= 15 else 'media'
                    )
                    for admin in admins:
                        n = criar_notificacao(
                            usuario=admin,
                            titulo=f'EPI vence em {dias_restantes}d: {epi_nome}',
                            tipo='sistema',
                            categoria='sistema',
                            prioridade=prioridade,
                            mensagem=(
                                f'{funcionario} - {epi_nome} '
                                f'vence em {vencimento.strftime("%d/%m/%Y")}.'
                            ),
                            url_destino=f'/seguranca/ficha/{entrega.ficha.pk}/'
                            if entrega.ficha else None,
                            icone='bi-shield-exclamation',
                        )
                        if n:
                            count += 1

        except ImportError:
            self.stdout.write(self.style.WARNING(
                '⚠️  App seguranca_trabalho não encontrada, pulando EPIs.'
            ))

        return count

    def _verificar_cas_vencendo(self, hoje):
        """Verifica CAs (Certificado de Aprovação) próximos do vencimento."""
        count = 0
        try:
            from seguranca_trabalho.models import Equipamento

            equipamentos = Equipamento.objects.filter(
                data_validade_ca__isnull=False,
                data_validade_ca__lte=hoje + timedelta(days=60),
                ativo=True,
            )

            admins = list(self._get_admins_e_seguranca())

            for eq in equipamentos:
                dias = (eq.data_validade_ca - hoje).days
                if dias > 60:
                    continue

                prioridade = 'critica' if dias <= 0 else (
                    'alta' if dias <= 15 else 'media'
                )
                status_texto = (
                    f'VENCIDO há {abs(dias)} dias'
                    if dias < 0
                    else f'vence em {dias} dias'
                )

                for admin in admins:
                    n = criar_notificacao(
                        usuario=admin,
                        titulo=f'CA {status_texto}: {eq.nome[:35]}',
                        tipo='sistema',
                        categoria='sistema',
                        prioridade=prioridade,
                        mensagem=(
                            f'CA {eq.certificado_aprovacao} do '
                            f'{eq.nome} - Validade: '
                            f'{eq.data_validade_ca.strftime("%d/%m/%Y")}.'
                        ),
                        url_destino=f'/seguranca/equipamento/{eq.pk}/',
                        icone='bi-file-earmark-x'
                        if dias < 0 else 'bi-file-earmark-exclamation',
                    )
                    if n:
                        count += 1

        except ImportError:
            pass

        return count

    def _verificar_pgr_vencendo(self, hoje):
        """Verifica PGRs próximos ao vencimento."""
        count = 0
        try:
            from pgr_gestao.models import PGRDocumento

            pgrs = PGRDocumento.objects.filter(
                data_vencimento__lte=hoje + timedelta(days=30),
                data_vencimento__gt=hoje,
                status='vigente',
            )

            for pgr in pgrs:
                dias = (pgr.data_vencimento - hoje).days
                if hasattr(pgr, 'criado_por') and pgr.criado_por:
                    n = notificar_pgr_vencimento(pgr, pgr.criado_por, dias)
                    if n:
                        count += 1

        except ImportError:
            self.stdout.write(self.style.WARNING(
                '⚠️  App pgr_gestao não encontrada, pulando.'
            ))

        return count

    def _verificar_planos_atrasados(self, hoje):
        """Verifica planos de ação PGR atrasados."""
        count = 0
        try:
            from pgr_gestao.models import PlanoAcaoPGR

            planos = PlanoAcaoPGR.objects.filter(
                status__in=['pendente', 'em_andamento'],
                data_prevista__lt=hoje,
            ).select_related('risco_identificado__pgr_documento')

            for plano in planos:
                if hasattr(plano, 'criado_por') and plano.criado_por:
                    n = notificar_pgr_plano_atrasado(plano, plano.criado_por)
                    if n:
                        count += 1

        except ImportError:
            pass

        return count

    def _verificar_treinamentos_vencendo(self, hoje):
        """Verifica treinamentos com vencimento próximo (30 dias) ou vencidos."""
        count = 0
        try:
            from treinamentos.models import Treinamento

            treinamentos = Treinamento.objects.filter(
                data_vencimento__isnull=False,
                data_vencimento__lte=hoje + timedelta(days=30),
                data_vencimento__gte=hoje - timedelta(days=7),
            )

            admins = list(self._get_admins_e_seguranca())

            for treinamento in treinamentos:
                dias = (treinamento.data_vencimento - hoje).days
                prioridade = 'critica' if dias < 0 else (
                    'alta' if dias <= 7 else 'media'
                )
                status_texto = (
                    f'VENCIDO há {abs(dias)}d'
                    if dias < 0
                    else f'vence em {dias}d'
                )
                nome = str(treinamento)[:40]

                for admin in admins:
                    n = criar_notificacao(
                        usuario=admin,
                        titulo=f'Treinamento {status_texto}: {nome}',
                        tipo='sistema',
                        categoria='sistema',
                        prioridade=prioridade,
                        mensagem=(
                            f'{nome} - Vencimento: '
                            f'{treinamento.data_vencimento.strftime("%d/%m/%Y")}'
                        ),
                        icone='bi-mortarboard',
                    )
                    if n:
                        count += 1

        except (ImportError, Exception) as e:
            self.stdout.write(self.style.WARNING(
                f'⚠️  Treinamentos: {e}'
            ))

        return count


