
from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Marca tarefas com prazo vencido como atrasadas'

    def handle(self, *args, **options):
        inicio = timezone.now()
        self.stdout.write(f"[{inicio}] Iniciando marcação de tarefas atrasadas...")
        
        try:
            # Importa a função real (refatore a task para reusar lógica)
            from tarefas.tasks import marcar_tarefas_atrasadas
            resultado = marcar_tarefas_atrasadas()  # chama síncrono, não .delay()
            
            self.stdout.write(self.style.SUCCESS(
                f"✅ Concluído em {(timezone.now()-inicio).total_seconds():.1f}s | {resultado}"
            ))
        except Exception as e:
            logger.exception("Erro ao marcar tarefas atrasadas")
            self.stderr.write(self.style.ERROR(f"❌ Erro: {e}"))
            raise

