
# ferramentas/management/commands/generate_qrcodes.py

from django.core.management.base import BaseCommand
from ferramentas.models import Ferramenta
from django.db.models import Q

class Command(BaseCommand):
    help = 'Gera QR Codes para todas as ferramentas que ainda não possuem um.'

    def handle(self, *args, **kwargs):
        # Usamos _base_manager para garantir que pegamos todas as ferramentas,
        # ignorando filtros de filial do manager padrão.
        ferramentas_sem_qr = Ferramenta._base_manager.filter(
            Q(qr_code__isnull=True) | Q(qr_code='')
        )

        count = ferramentas_sem_qr.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('Todas as ferramentas já possuem QR Code.'))
            return

        self.stdout.write(f'Encontradas {count} ferramentas sem QR Code. Gerando agora...')

        for ferramenta in ferramentas_sem_qr:
            try:
                # Ao salvar, a lógica no método save() do modelo será acionada
                ferramenta.save()
                self.stdout.write(f'  - QR Code gerado para: {ferramenta.nome} ({ferramenta.codigo_identificacao})')
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'  - Falha ao gerar para {ferramenta.nome}: {e}'))

        self.stdout.write(self.style.SUCCESS('Processo de geração de QR Codes concluído!'))
