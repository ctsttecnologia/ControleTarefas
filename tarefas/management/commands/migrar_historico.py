
# tarefas/management/commands/migrar_historico.py

from django.core.management.base import BaseCommand
from tarefas.models import HistoricoStatus, HistoricoTarefa, Tarefas


class Command(BaseCommand):
    help = 'Migra dados do HistoricoStatus antigo para HistoricoTarefa'

    def handle(self, *args, **options):
        status_dict = dict(Tarefas.STATUS_CHOICES)
        total = HistoricoStatus.objects.count()
        migrados = 0

        for h in HistoricoStatus.objects.select_related('tarefa', 'alterado_por', 'filial').iterator():
            anterior_display = status_dict.get(h.status_anterior, h.status_anterior)
            novo_display = status_dict.get(h.novo_status, h.novo_status)

            _, created = HistoricoTarefa.objects.get_or_create(
                tarefa=h.tarefa,
                alterado_por=h.alterado_por,
                data_alteracao=h.data_alteracao,
                defaults={
                    'tipo_alteracao': 'status',
                    'campo_alterado': 'status',
                    'valor_anterior': anterior_display,
                    'valor_novo': novo_display,
                    'descricao': f'Status: {anterior_display} → {novo_display}',
                    'filial': h.filial,
                }
            )
            if created:
                migrados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Migração concluída: {migrados}/{total} registros migrados.'
        ))

